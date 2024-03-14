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
import src.mic
import src.recognition as recognition
import src.output as output
import src.val as val
import src.google_recognizers as google
import src.exception
from src.cancellation import CancellationObject
from src.main_common import Record, save_wav
from src.filter import NoiseFilter

def run(
    mic:src.mic.Mic,
    recognition_model:recognition.RecognitionModel,
    outputer:output.RecognitionOutputer,
    filters:list[NoiseFilter],
    record:Record,
    env:Enviroment,
    cancel:CancellationObject,
    is_test:bool,
    logger:Logger,
    _:str) -> None:
    """
    メイン実行
    """

    thread_pool = ThreadPoolExecutor(max_workers=1)
    def onrecord(index:int, param:src.mic.ListenResultParam) -> None:
        """
        マイク認識データが返るコールバック関数
        """
        def filter(ary:np.ndarray) -> np.ndarray:
            """
            フィルタ処理をする
            """
            if len(filters) == 0:
                return ary
            else:
                fft = np.fft.fft(ary)
                for f in filters:
                    f.filter(fft)
                return np.real(np.fft.ifft(fft))
        class PerformanceResult(NamedTuple):
            result:Any
            time:float
        def performance(func:Callable[[], Any]) ->  PerformanceResult:
            """
            funcを実行した時間を計測
            """
            import time
            start = time.perf_counter() 
            r = func()
            return PerformanceResult(r, time.perf_counter()-start)
        log_mic_info = mic.current_param
        log_info_mic = f"current energy_threshold = {log_mic_info.energy_threshold}"
        log_info_recognition = recognition_model.get_log_info()

        insert:str
        if 0 < mic.end_insert_sec:
            insert = f", {round(mic.end_insert_sec, 2)}s挿入"
        else:
            insert = ""
        if not param.energy is None:
            insert = f"{insert}, dB={rms2db(param.energy.value):.2f}"
        data = param.pcm
        pcm_sec = len(data) / 2 / mic.sample_rate
        logger.debug(f"#録音データ取得(#{index}, time={dt.datetime.now()}, pcm={(int)(len(data)/2)}, {round(pcm_sec, 2)}s{insert})")
        r = PerformanceResult(None, -1)
        log_exception:Exception | None = None
        try:
            save_wav(record, index, data, mic.sample_rate, 2, logger)
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

            r = performance(lambda: recognition_model.transcribe(filter(np.frombuffer(d, np.int16).flatten())))
            assert(isinstance(r.result, recognition.TranscribeResult)) # ジェネリクス使った型定義の方法がわかってないのでassert置いて型を確定させる
            if r.result.transcribe not in ["", " ", "\n", None]:
                logger.notice(f"認識時間[{round(r.time, 2)}s],PCM[{round(pcm_sec, 2)}s],{round(r.time/pcm_sec, 2)}tps", end=": ")
                outputer.output(r.result.transcribe)
            if not r.result.extend_data is None:
                logger.debug(f"{r.result.extend_data}")
        except recognition.TranscribeException as e:
            log_exception = e
            if e.inner is None:
                logger.info(e.message)
            else:
                if isinstance(e.inner, urlerr.HTTPError) or isinstance(e.inner, urlerr.URLError):
                    logger.notice(e.message)
                elif isinstance(e.inner, google.UnknownValueError):
                    raw = e.inner.raw_data
                    if raw is None:
                        logger.debug(f"#{e.message}")
                    else:
                        logger.debug(f"#{e.message}{os.linesep}{raw}")
                else:
                    logger.debug(f"#{e.message}")
                    logger.debug(f"#{type(e.inner)}:{e.inner}")
        except output.WsOutputException as e:
            log_exception = e
            logger.info(e.message)
            if not e.inner is None:
                logger.debug(f"# => {type(e.inner)}:{e.inner}")
        except Exception as e:
            log_exception = e
            logger.error([
                f"!!!!意図しない例外!!!!",
                f"{type(e)}:{e}",
                traceback.format_exc()
            ])
        for it in [("", mic.get_verbose(env.verbose)), ("", recognition_model.get_verbose(env.verbose))]:
            pass
        logger.debug(f"#認識処理終了(#{index}, time={dt.datetime.now()})")

        # ログ出力
        try:
            log_transcribe = " - "
            log_time = " - "
            log_exception_s = " - "
            log_insert:str
            if not r.result is None:
                assert(isinstance(r.result, recognition.TranscribeResult)) # ジェネリクス使った型定義の方法がわかってないのでassert置いて型を確定させる
                if r.result.transcribe not in ["", " ", "\n", None]:
                    log_transcribe = r.result.transcribe
                if not r.result.extend_data is None:
                    log_transcribe = f"{log_transcribe}{os.linesep}{r.result.extend_data}"
                log_time = f"{round(r.time, 2)}s {round(r.time/pcm_sec, 2)}tps"
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
            log_en_info = " - "
            if not param.energy is None:
                log_insert = f"{log_insert}, dB={rms2db(param.energy.value):.2f}dB"
                log_en_info = f"energy={round(param.energy.value, 2)}, max={round(param.energy.max, 2)}, min={round(param.energy.min, 2)}"

            logger.log([
                f"認識処理　　　　 : #{index}",
                f"録音情報　　　　 : {round(pcm_sec, 2)}s{log_insert}, {(int)(len(data)/2)}sample / {mic.sample_rate}Hz",
                f"音エネルギー生値 : {log_en_info}",
                f"認識結果　　　　 : {log_transcribe}",
                f"認識時間　　　　 : {log_time}",
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

    def onrecord_async(index:int, data:src.mic.ListenResultParam) -> None:
        """
        マイク認識データが返るコールバック関数の非同期版
        """
        thread_pool.submit(onrecord, index, data)

    try:
        if is_test:
            mic.listen(onrecord)
        else:
            mic.listen_loop(onrecord_async, cancel)
    finally:
        thread_pool.shutdown()