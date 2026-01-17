import os
import sys
import platform
import traceback
import click
import speech_recognition
import urllib.error as urlerr
import multiprocessing
import audioop
import numpy as np
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Iterable, Optional, NamedTuple


from src import Logger, Enviroment, db2rms, rms2db
import src.microphone
import src.recognition as recognition
import src.recognition_translate as recognition_translate
import src.output as output
import src.output_subtitle as output_subtitle
import src.val as val
import src.google_recognizers as google
import src.exception
import src.filter_transcribe as filter_t
from src.cancellation import CancellationObject
from src.main_common import Record, save_wav

def run(
    mic:src.microphone.Microphone,
    recognition_model:recognition.RecognitionModel,
    translate_model:None|recognition_translate.TranslateModel,
    filter_transcribe:filter_t.TranscribeFilter,
    outputers:list[output.RecognitionOutputer],
    record:Record,
    env:Enviroment,
    cancel:CancellationObject,
    logger:Logger,
    _:str) -> None:
    """
    メイン実行
    """

    thread_pool = ThreadPoolExecutor(max_workers=1)
    def onrecord(index:int, param:src.microphone.ListenResultParam) -> None:
        """
        マイク認識データが返るコールバック関数
        """
        class PerformanceResult(NamedTuple):
            result:Any
            time:float
        
        def fill_right(text:str) -> str:
            import re
            l = sum(map(lambda x: 1 if ord(x) < 256 else 2, re.sub("\033\\[[^m]+m", "", text)))
            if l < 80:
                return text + "".join(map(lambda _: " ", range(80 - l)))
            else:
                return text

        def performance(func:Callable[[], Any]) ->  PerformanceResult:
            """
            funcを実行した時間を計測
            """
            import time
            start = time.perf_counter() 
            r = func()
            return PerformanceResult(r, time.perf_counter()-start)

        log_info_mic = f"current energy_threshold = {mic.energy_threshold}"
        log_info_recognition = recognition_model.get_log_info()

        insert:str
        if 0 < mic.start_insert_sec or 0 < mic.end_insert_sec:
            insert = f", {round(mic.start_insert_sec, 2)}s+{round(mic.end_insert_sec, 2)}s挿入"
        else:
            insert = ""

        #if not param.energy is None:
        #    insert = f"{insert}, dB={rms2db(param.energy.value):.2f}"
        data = param.pcm
        pcm_sec = len(data) / 2 / mic.sample_rate
        logger.debug(
            f"#録音データ取得(#{index}, time={dt.datetime.now()}, pcm={(int)(len(data)/2)}, {round(pcm_sec, 2)}s{insert})",
            console=val.Console.DefaultColor,
            reset_console=True)
        r = PerformanceResult(None, -1)
        rr:PerformanceResult =  PerformanceResult(None, -1)
        translate = ""
        transcribe_filter = ""
        log_exception:Exception | None = None
        try:
            save_wav(record, index, data, mic.sample_rate, 2, logger)
            # 長さチェック
            if (pcm_sec - (mic.start_insert_sec + mic.end_insert_sec)) < mic.record_min_sec:
                raise recognition.TranscribeException(f"録音データが短いためスキップ({round(pcm_sec, 2)}s)")

            # 認識用音声データ
            if recognition_model.required_sample_rate is None or mic.sample_rate == recognition_model.required_sample_rate:
                d = data
            else:
                d, _ = audioop.ratecv(
                    data,
                    2, # sample_width
                    1,
                    mic.sample_rate,
                    recognition_model.required_sample_rate,
                    None)
            # 翻訳用音声データ
            if translate_model == None:
                dd = None
            elif translate_model.required_sample_rate is None:
                dd = data
            elif recognition_model.required_sample_rate == translate_model.required_sample_rate:
                dd = d
            else:
                dd, _ = audioop.ratecv(
                    data,
                    2, # sample_width
                    1,
                    mic.sample_rate,
                    translate_model.required_sample_rate,
                    None)
            r = performance(lambda: recognition_model.transcribe(np.frombuffer(d, np.int16).flatten()))
            assert(isinstance(r.result, recognition.TranscribeResult)) # ジェネリクス使った型定義の方法がわかってないのでassert置いて型を確定させる
            if r.result.transcribe not in ["", " ", "\n", None]:
                def green(o:object, dg:str = "") -> str:
                    return f"{val.Console.Green.value}{o}{dg}{val.Console.Reset.value}"
                if env.verbose == val.VERBOSE_INFO:
                    logger.notice(f"#{index}", end=" ")
                logger.notice(fill_right(f"認識時間[{green(round(r.time, 2), 's')}],PCM[{green(round(pcm_sec, 2), 's')}],{green(round(r.time/pcm_sec, 2), 'tps')}: {r.result.transcribe}"), console=val.Console.DefaultColor)

                if translate_model != None:
                    rr = performance(lambda: translate_model.translate(np.frombuffer(dd, np.int16).flatten(), r.result.transcribe )) # type: ignore
                    assert(isinstance(rr.result, recognition_translate.TranslateResult))
                    translate = rr.result.translate

                    if env.verbose == val.VERBOSE_INFO:
                        logger.notice(f"#{index}", end=" ")
                    logger.notice(fill_right(f"翻訳時間[{green(round(rr.time, 2), 's')}],PCM[{green(round(pcm_sec, 2), 's')}],{green(round(rr.time/pcm_sec, 2), 'tps')}: {translate}"))
            if not r.result.extend_data is None:
                logger.trace(f"${r.result.extend_data}")

            transcribe_filter:str = r.result.transcribe
            if filter_transcribe.has_rule:
                transcribe_filter = filter_transcribe.filter(r.result.transcribe)
                if env.verbose == val.VERBOSE_INFO:
                    logger.notice(f"#{index}", end=" ")
                logger.notice(fill_right(f"フィルタ: {transcribe_filter}"))
            if transcribe_filter != "":
                for ot in outputers:
                    ot.output(transcribe_filter, translate)
        except recognition.TranscribeException as e:
            if env.verbose == val.VERBOSE_INFO:
                logger.notice(f"#{index}", end=" ")
            logger.notice("認識失敗".ljust(40, "　"), console=val.Console.Yellow, reset_console=True)
            log_exception = e
            if e.inner is None:
                logger.info(e.message, console=[val.Console.Yellow, val.Console.BackgroundBlack, val.Console.UnderLine], reset_console=True)
            else:
                if isinstance(e.inner, urlerr.HTTPError) or isinstance(e.inner, urlerr.URLError):
                    logger.notice(e.message, console=[val.Console.Yellow, val.Console.BackgroundBlack, val.Console.UnderLine], reset_console=True)

                elif isinstance(e.inner, google.UnknownValueError):
                    raw = e.inner.raw_data
                    if raw is None:
                        logger.trace(f"${e.message}")
                    else:
                        logger.trace(f"${e.message}{os.linesep}{raw}")
                else:
                    logger.trace(f"#{e.message}")
                    logger.trace(f"#{type(e.inner)}:{e.inner}")
        except output.WsOutputException as e:
            log_exception = e
            logger.info("!!!!連携失敗!!!!", console=val.Console.Red)
            logger.info(e.message, console=val.Console.Red, reset_console=True)
            if not e.inner is None:
                logger.trace(f"$ => {type(e.inner)}:{e.inner}", console=val.Console.Red, reset_console=True)
        except Exception as e:
            log_exception = e
            logger.error([
                f"!!!!意図しない例外!!!!",
                f"{type(e)}:{e}",
                traceback.format_exc()
            ])
        logger.print(val.Console.Reset.value, end="") # まとめてコンソールの設定を解除する
        logger.debug(f"#認識終了(#{index}, time={dt.datetime.now()})", console=val.Console.DefaultColor, reset_console=True)

        # ログ出力
        try:
            log_transcribe = " - "
            log_transcribe_filter = " - "
            log_translate = " - "
            log_time = " - "
            log_time_translate = " - "
            log_exception_s = " - "
            log_insert:str
            log_en_info = " - "
            if not r.result is None:
                assert(isinstance(r.result, recognition.TranscribeResult)) # ジェネリクス使った型定義の方法がわかってないのでassert置いて型を確定させる
                if r.result.transcribe not in ["", " ", "\n", None]:
                    log_transcribe = r.result.transcribe
                if not r.result.extend_data is None:
                    log_transcribe = f"{log_transcribe}{os.linesep}{r.result.extend_data}"
                log_time = f"{round(r.time, 2)}s {round(r.time/pcm_sec, 2)}tps"
                log_transcribe_filter = transcribe_filter
            if not rr.result is None:
                assert(isinstance(rr.result, recognition_translate.TranslateResult))
                log_translate = rr.result.translate
                log_time_translate = f"{round(rr.time, 2)}s {round(rr.time/pcm_sec, 2)}tps"
            if not log_exception is None:
                log_exception_s = f"{type(log_exception)}"
                if isinstance(log_exception, src.exception.IlluminateException):
                    log_exception_s = f"{log_exception}:{log_exception.message}{os.linesep}inner = {type(log_exception.inner)}:{log_exception.inner}"
                else:
                    log_exception_s = f"{log_exception}:{log_exception}"
                if isinstance(log_exception, recognition.TranscribeException):
                    log_transcribe = " -失敗- "
            if 0 < mic.end_insert_sec:
                log_insert = f"({round(mic.end_insert_sec, 2)}s挿入)"
            else:
                log_insert = ""
            if not param.energy is None:
                log_insert = f"{log_insert}, dB={rms2db(param.energy.value):.2f}dB"
                log_en_info = f"energy={round(param.energy.value, 2)}, max={round(param.energy.max, 2)}, min={round(param.energy.min, 2)}"

            logger.log([
                f"認識処理　　　　 : #{index}",
                f"録音情報　　　　 : {round(pcm_sec, 2)}s{log_insert}, {(int)(len(data)/2)}sample / {mic.sample_rate}Hz",
                f"音エネルギー生値 : {log_en_info}",
                f"認識結果　　　　 : {log_transcribe}",
                f"認識時間　　　　 : {log_time}",
                f"翻訳結果　　　　 : {log_translate}",
                f"翻訳時間　　　　 : {log_time_translate}",
                f"フィルタ結果　　 : {log_transcribe_filter}",
                f"例外情報　　　　 : {log_exception_s}",
                f"マイク情報　　　 : {log_info_mic}",
                f"認識モデル情報　 : {log_info_recognition}",
            ])
        except Exception as e_: # eにするとPylanceの動きがおかしくなるので名前かえとく
            logger.error([
                f"!!!!ログ出力例外!!!!",
                f"({type(e_)}:{e_})",
                traceback.format_exc()
             ])

    def onrecord_async(index:int, data:src.microphone.ListenResultParam) -> None:
        """
        マイク認識データが返るコールバック関数の非同期版
        """
        thread_pool.submit(onrecord, index, data)

    try:
        mic.listen(onrecord_async, cancel)
    finally:
        thread_pool.shutdown()