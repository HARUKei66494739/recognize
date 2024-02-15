#!/usr/bin/env python3

import os
import sys
import platform
import traceback
import click
import torch
import speech_recognition
import urllib.error as urlerr
import multiprocessing
import audioop
import numpy as np
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Iterable, Optional, NamedTuple

from . import Logger, Enviroment
import src.mic
import src.recognition as recognition
import src.output as output
import src.val as val
import src.google_recognizers as google
import src.exception
from src.cancellation import CancellationObject
from src.filter import *

class Record(NamedTuple):
    """
    録音設定
    """
    is_record:bool
    file:str
    directory:str

@click.command()
@click.option("--test", default="", help="テストを行います",type=click.Choice(["", val.TEST_VALUE_RECOGNITION, val.TEST_VALUE_MIC]))
@click.option("--method", default=val.METHOD_VALUE_WHISPER_FASTER, help="使用する認識方法", type=click.Choice([val.METHOD_VALUE_WHISPER, val.METHOD_VALUE_WHISPER_FASTER, val.METHOD_VALUE_GOOGLE, val.METHOD_VALUE_GOOGLE_DUPLEX]))
@click.option("--whisper_model", default="medium", help="(whisper)使用する推論モデル", type=click.Choice(["tiny","base", "small","medium","large","large-v2","large-v3"]))
@click.option("--whisper_device", default=("cuda" if torch.cuda.is_available() else "cpu"), help="(whisper)使用する演算装置", type=click.Choice(["cpu","cuda"]))
@click.option("--whisper_language", default="", help="(whisper)音声解析対象の言語", type=click.Choice(val.LANGUAGE_CODES))
@click.option("--google_language", default="ja-JP", help="(google)音声解析対象の言語", type=str)
@click.option("--google_timeout", default=5.0, help="(google)最大認識待ち時間", type=float)
@click.option("--google_convert_sampling_rate", default=False, help="(google)マイク入力を16kに変換します", is_flag=True, type=bool)
@click.option("--google_error_retry", default=1, help="(google)500エラー時にリトライ試行する回数", type=int)
@click.option("--google_duplex_parallel", default=False, help="(google_duplexのみ)複数並列リクエストを投げエラーの抑制を図ります", is_flag=True, type=bool)
@click.option("--google_duplex_parallel_max", default=None, help="(google_duplexのみ)複数並列リクエスト数増減時の最大並列数", type=int)
@click.option("--google_duplex_parallel_reduce_count", default=None, help="(google_duplexのみ)増加した並列数を減少するために必要な成功数", type=int)
@click.option("--mic", default=None, help="使用するマイクのindex", type=int)
@click.option("--mic_energy", default=300, help="設定した値より小さいマイク音量を無音として扱います", type=float)
@click.option("--mic_ambient_noise_to_energy", default=False, help="環境音から--mic_energyを自動的に設定します", is_flag=True, type=bool)
@click.option("--mic_dynamic_energy", default=False, is_flag=True, help="Trueの場合周りの騒音に基づいてマイクのエネルギーレベルを動的に変更します", type=bool)
@click.option("--mic_dynamic_energy_ratio", default=None, help="--mic_dynamic_energyで--mic_energyを変更する場合の最小係数", type=float)
@click.option("--mic_dynamic_energy_adjustment_damping", default=None, help="-", type=float)
@click.option("--mic_dynamic_energy_min", default=100, help="--mic_dynamic_energyを指定した場合動的設定される--mic_energy最低値", type=float)
@click.option("--mic_pause", default=0.8, help="無音として認識される秒数を指定します", type=float)
@click.option("--mic_phrase", default=None, help="発話音声として認識される最小秒数", type=float)
@click.option("--mic_non_speaking", default=None, help="-", type=float)
@click.option("--mic_sampling_rate", default=16000, help="-", type=int)
@click.option("--mic_listen_interval", default=0.25, help="マイク監視ループで1回あたりのマイクデバイス監視間隔(秒)", type=float)
@click.option("--out", default=val.OUT_VALUE_PRINT, help="認識結果の出力先", type=click.Choice([val.OUT_VALUE_PRINT,val.OUT_VALUE_YUKARINETTE, val.OUT_VALUE_YUKACONE]))
@click.option("--out_yukarinette",default=49513, help="ゆかりねっとの外部連携ポートを指定", type=int)
@click.option("--out_yukacone",default=None, help="ゆかコネNEOの外部連携ポートを指定", type=int)
#@click.option("--out_illuminate",default=495134, help="未実装",type=int)
@click.option("--filter_lpf_cutoff", default=200, help="ローパスフィルタのカットオフ周波数を設定", type=int)
@click.option("--filter_lpf_cutoff_upper", default=200, help="ローパスフィルタのカットオフ周波数(アッパー)を設定", type=int)
@click.option("--filter_hpf_cutoff", default=200, help="ハイパスフィルタのカットオフ周波数を設定します", type=int)
@click.option("--filter_hpf_cutoff_upper", default=200, help="ハイパスフィルタのカットオフ周波数(アッパー)を設定", type=int)
@click.option("--disable_lpf", default=False, help="ローパスフィルタを使用しません", is_flag=True, type=bool)
@click.option("--disable_hpf", default=False, help="ハイパスフィルタを使用しません", is_flag=True, type=bool)
@click.option("--print_mics",default=False, help="マイクデバイスの一覧をプリント", is_flag=True, type=bool)
@click.option("--list_devices",default=False, help="(廃止予定)--print_micsと同じ", is_flag=True, type=bool)
@click.option(val.ARG_NAME_VERBOSE, default=val.ARG_DEFAULT_VERBOSE, help="出力ログレベルを指定", type=click.Choice(val.ARG_CHOICE_VERBOSE))
@click.option(val.ARG_NAME_LOG_FILE, default=val.ARG_DEFAULT_LOG_FILE, help="ログファイルの出力ファイル名を指定します", type=str)
@click.option(val.ARG_NAME_LOG_DIRECTORY, default=val.ARG_DEFAULT_LOG_DIRECTORY, help="ログ格納先のディレクトリを指定します", type=str)
@click.option("--record",default=False, help="録音した音声をファイルとして出力します", is_flag=True, type=bool)
@click.option("--record_file", default="record", help="録音データの出力ファイル名を指定します", type=str)
@click.option("--record_directory", default=None, help="録音データの出力先ディレクトリを指定します", type=str)
@click.option("--feature", default="", help="-", type=str) 
def main(
    test:str,
    method:str,
    whisper_model:str,
    whisper_device:str,
    whisper_language:str,
    google_language:str,
    google_timeout:float,
    google_convert_sampling_rate:bool,
    google_error_retry:int,
    google_duplex_parallel:bool,
    google_duplex_parallel_max:Optional[int],
    google_duplex_parallel_reduce_count:Optional[int],
    mic:Optional[int],
    mic_energy:float,
    mic_ambient_noise_to_energy:bool,
    mic_dynamic_energy:bool,
    mic_dynamic_energy_ratio:Optional[float],
    mic_dynamic_energy_adjustment_damping:Optional[float],
    mic_dynamic_energy_min:float,
    mic_pause:float,
    mic_phrase:Optional[float],
    mic_non_speaking:Optional[float],
    mic_sampling_rate:int,
    mic_listen_interval:float,
    out:str,
    out_yukarinette:int,
    out_yukacone:Optional[int],
#    out_illuminate:int,
    filter_lpf_cutoff:int,
    filter_lpf_cutoff_upper:int,
    filter_hpf_cutoff:int,
    filter_hpf_cutoff_upper:int,
    disable_lpf:bool,
    disable_hpf:bool,
    print_mics:bool,
    list_devices:bool,
    verbose:str,
    log_file:str,
    log_directory:Optional[str],
    record:bool,
    record_file:str,
    record_directory:Optional[str],
    feature:str
    ) -> None:
    from . import ilm_logger, ilm_enviroment

    if not ilm_enviroment.is_exe:
        os.makedirs(ilm_enviroment.root, exist_ok=True)
        os.chdir(ilm_enviroment.root)

    ilm_logger.log([
        "起動",
        f"platform = {platform.platform()}",
        f"python = {sys.version}",
        f"arg = {sys.argv}",
    ])

    if print_mics or list_devices:
        __main_print_mics(ilm_logger, feature)
        return
    
    if is_feature(feature, "ambient"):
        __main_print_ambient(
            mic,
            mic_sampling_rate,
            mic_dynamic_energy_ratio,
            mic_dynamic_energy_adjustment_damping,
            3.0,
            ilm_logger,
            feature)
        pass

    cancel = CancellationObject()
    cancel_mp = multiprocessing.Value("i", 1)
    try:
        if record_directory is None:
            record_directory = ilm_enviroment.root
        else:
            os.makedirs(record_directory, exist_ok=True)
        sampling_rate = src.mic.Mic.update_sample_rate(mic, mic_sampling_rate) #16000
        rec = Record(record, record_file, record_directory)

        ilm_logger.print("マイクの初期化")
        mc = src.mic.Mic(
            sampling_rate,
            mic_ambient_noise_to_energy,
            mic_energy,
            mic_pause,
            mic_dynamic_energy,
            mic_dynamic_energy_ratio,
            mic_dynamic_energy_adjustment_damping,
            mic_dynamic_energy_min,
            mic_phrase,
            mic_non_speaking,
            mic_listen_interval,
            mic)
        ilm_logger.print(f"マイクは{mc.device_name}を使用します")
        ilm_logger.debug(f"input energy={mic_energy}")
        ilm_logger.debug(f"current energy=-")

        if test == val.TEST_VALUE_MIC:
            __main_test_mic(mc, rec, cancel, feature)
        #elif is_feature(feature, "mp"):
        #    ilm_logger.print("実験的機能：マルチプロセスでマイクの監視を行います")
        #    ilm_logger.print("--recordは実装されていません")
        #
        #    q = multiprocessing.Queue()
        #    p = multiprocessing.Process(target=src.mp.main_feature_mp, args=(
        #        q,
        #        cancel_mp,
        #        sampling_rate,
        #        method,
        #        whisper_model,
        #        whisper_language,
        #        whisper_device,
        #        google_convert_sampling_rate,
        #        google_language,
        #        google_timeout,
        #        google_error_retry,
        #        google_duplex_parallel,
        #        out,
        #        out_yukarinette,
        #        out_yukacone,
        #        disable_lpf,
        #        filter_lpf_cutoff,
        #        filter_lpf_cutoff_upper,
        #        disable_hpf,
        #        filter_hpf_cutoff,
        #        filter_hpf_cutoff_upper,
        #        0,
        #        logger,
        #        verbose,
        #        feature))
        #    p.daemon = True
        #    p.start()
        #    mc.listen_loop_mp(q, cancel_mp)
        else:
            ilm_logger.print("認識モデルの初期化")
            recognition_model:recognition.RecognitionModel = {
                val.METHOD_VALUE_WHISPER: lambda: recognition.RecognitionModelWhisper(
                    model=whisper_model,
                    language=whisper_language,
                    device=whisper_device,
                    download_root=f"{ilm_enviroment.root}{os.sep}.cache"),
                val.METHOD_VALUE_WHISPER_FASTER: lambda:  recognition.RecognitionModelWhisperFaster(
                    model=whisper_model,
                    language=whisper_language,
                    device=whisper_device,
                    download_root=f"{ilm_enviroment.root}{os.sep}.cache"),
                val.METHOD_VALUE_GOOGLE: lambda: recognition.RecognitionModelGoogle(
                    sample_rate=sampling_rate,
                    sample_width=2,
                    convert_sample_rete=google_convert_sampling_rate,
                    language=google_language,
                    timeout=google_timeout if 0 < google_timeout else None,
                    challenge=google_error_retry),
                val.METHOD_VALUE_GOOGLE_DUPLEX: lambda: recognition.RecognitionModelGoogleDuplex(
                    sample_rate=sampling_rate,
                    sample_width=2,
                    convert_sample_rete=google_convert_sampling_rate,
                    language=google_language,
                    timeout=google_timeout if 0 < google_timeout else None,
                    challenge=google_error_retry,
                    is_parallel_run=google_duplex_parallel,
                    parallel_max=google_duplex_parallel_max,
                    parallel_reduce_count=google_duplex_parallel_reduce_count),
            }[method]()
            ilm_logger.debug(f"#認識モデルは{type(recognition_model)}を使用")

            outputer:output.RecognitionOutputer = {
                val.OUT_VALUE_PRINT: lambda: output.PrintOutputer(),
                val.OUT_VALUE_YUKARINETTE: lambda: output.YukarinetteOutputer(f"ws://localhost:{out_yukarinette}", lambda x: ilm_logger.info(x)),
                val.OUT_VALUE_YUKACONE: lambda: output.YukaconeOutputer(f"ws://localhost:{output.YukaconeOutputer.get_port(out_yukacone)}", lambda x: ilm_logger.info(x)),
    #            val.OUT_VALUE_ILLUMINATE: lambda: output.IlluminateSpeechOutputer(f"ws://localhost:{out_illuminate}"),
            }[out]()
            ilm_logger.debug(f"#出力は{type(outputer)}を使用")

            filters:list[NoiseFilter] = []
            if not disable_lpf:
                filters.append(
                    LowPassFilter(
                        sampling_rate,
                        filter_lpf_cutoff,
                        filter_lpf_cutoff_upper))
            if not disable_hpf:
                filters.append(
                    HighPassFilter(
                        sampling_rate,
                        filter_hpf_cutoff,
                        filter_hpf_cutoff_upper))        
            ilm_logger.debug(f"#使用音声フィルタ({len(filters)}):")
            for f in filters:
               ilm_logger.debug(f"#{type(f)}")


            ilm_logger.log([
                f"マイク: {mc.device_name}",
                f"{mc.get_mic_info()}",
                f"認識モデル: {type(recognition_model)}",
                f"出力 = {type(outputer)}",
                f"フィルタ = {','.join(list(map(lambda x: f'{type(x)}', filters)))}"
            ])

            ilm_logger.print("認識中…")
            __main_run(
                mc,
                recognition_model,
                outputer,
                filters,
                rec,
                ilm_enviroment,
                cancel,
                test == val.TEST_VALUE_RECOGNITION,
                ilm_logger,
                feature)
    except src.mic.MicInitializeExeception as e:
        ilm_logger.print(e.message)
        ilm_logger.print(f"{type(e.inner)}{e.inner}")
    except KeyboardInterrupt:
        cancel.cancel()
        cancel_mp.value = 0 # type: ignore
        ilm_logger.print("ctrl+c")
    finally:
        pass
    sys.exit()


def __main_print_mics(logger:Logger, _:str) -> None:
    """
    マイク情報出力
    """
    audio = speech_recognition.Microphone.get_pyaudio().PyAudio()
    try:
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            index = device_info.get("index")
            host_api = device_info.get("hostApi")
            name = device_info.get("name")
            input = device_info.get("maxInputChannels")
            host_api_name = "-"
            rate = device_info.get("defaultSampleRate")
            if isinstance(host_api, int):
                host_api_name = audio.get_host_api_info_by_index(host_api).get("name")
            if isinstance(input, int) and 0 < input:
                logger.print(f"{index} : [{host_api_name}]{name} sample_rate={rate}")            
    finally:
        audio.terminate()

def __main_print_ambient(
        device:int|None,
        sample_rate:int,
        dynamic_energy_ratio:float|None,
        dynamic_energy_adjustment_damping:float|None,
        timeout:float,
        logger:Logger,
        _:str) -> None:
    import speech_recognition as sr
    import math
    def value(v:float|None, default:float) -> float: return v if not v is None else default

    rate = src.mic.Mic.update_sample_rate(device, sample_rate)
    mic = sr.Microphone(sample_rate = rate, device_index = device)

    logger.print("feature function:ambient")
    logger.print("exit ctrl+c")
    max_list:int = max(math.ceil(60 / timeout), 10) # 1分サンプル/最低10レコード保障
    try:
        def add(lst:list[Any], v:Any, max:int) -> None:
            lst.append(v)
            if max <= len(lst):
                lst.pop(-1)

        def add_top(lst:list[float], v:float, max:int) -> None:
            lst.append(v)
            lst.sort(reverse=True)
            if max <= len(lst):
                lst.pop(-1)
        
        def avg(lst:list[float]) -> float:
            total = 0
            for v in lst:
                total += v
            return total / len(lst)

        list_energys:list[tuple[float, float]] = []
        list_energys_top:list[float] = []
        list_energy_thresholds_top:list[float] = []
        while True:
            elapsed_time = 0
            energy_threshold = 0.0
            energy_total = 0.0
            dynamic_energy_ratio_ = value(dynamic_energy_ratio, 1.5)
            dynamic_energy_adjustment_damping_ = value(dynamic_energy_adjustment_damping, 0.15)

            with mic as source:
                logger.print(f"start record {round(timeout, 2)} sec")
                logger.print(f"mic record : {source.SAMPLE_RATE}Hz/{source.SAMPLE_WIDTH * 8}bit")
                logger.print(f"1 cycle record :{source.CHUNK}bytes")
                count = 0
                seconds_per_buffer = float(source.CHUNK) / source.SAMPLE_RATE
                while elapsed_time <= timeout:
                    count += 1
                    elapsed_time += seconds_per_buffer

                    buffer = source.stream.read(source.CHUNK) # type: ignore
                    if len(buffer) == 0:
                        break 
                    energy = audioop.rms(buffer, source.SAMPLE_WIDTH)
                    energy_total += energy
                    damping = dynamic_energy_adjustment_damping_ ** seconds_per_buffer 
                    target_energy = energy * dynamic_energy_ratio_
                    energy_threshold = energy_threshold * damping + target_energy * (1 - damping)
                
                energy_avg = energy_total  / count
                add(list_energys, (energy_avg, energy_threshold), max_list)
                add_top(list_energys_top, energy_avg, max_list)
                add_top(list_energy_thresholds_top, energy_threshold, max_list)
                logger.print("done.")
                logger.print("--------------------------------------")
                logger.print(f"input energy average       : {round(energy_avg, 2)}")
                logger.print(f"calcurate energy threshold : {round(energy_threshold, 2)}")
                logger.print("--------------------------------------")
                logger.print(f"energy average recent {max_list}              : {round(avg(list(map(lambda x: x[0], list_energys))), 2)}")
                logger.print(f"energy threshold average recent {max_list}    : {round(avg(list(map(lambda x: x[1], list_energys))), 2)}")
                logger.print(f"total energy average top {max_list}           : {round(avg(list_energys_top), 2)}")
                logger.print(f"total energy threshold average top {max_list} : {round(avg(list_energy_thresholds_top), 2)}")
                logger.print("--------------------------------------")
                logger.print("")
    except Exception as e:
        logger.print(f"except Exception as {type(e)}")
        logger.print(e)
        logger.print(traceback.format_exc())
    finally:
        logger.print("exit.")
        sys.exit()



def __main_test_mic(mic:src.mic.Mic, rec:Record, cancel:CancellationObject, _:str) -> None:
    """
    マイクテスト
    """
    def onrecord(index:int, param:src.mic.ListenResult) -> None:
        """
        マイク認識データが返るコールバック関数
        """
        save_wav(rec, index, param.audio, mic.sample_rate)

    mic.test_mic(cancel, onrecord)
    return

def __main_run(
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
    def onrecord(index:int, param:src.mic.ListenResult) -> None:
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

        insert:str
        if 0 < mic.end_insert_sec:
            insert = f", {round(mic.end_insert_sec, 2)}s挿入"
        else:
            insert = ""
        if not param.energy is None:
            insert = f"{insert}, energy={round(param.energy, 2)}"
        data = param.audio
        pcm_sec = len(data) / 2 / mic.sample_rate
        logger.debug(f"#録音データ取得(#{index}, time={dt.datetime.now()}, pcm={(int)(len(data)/2)}, {round(pcm_sec, 2)}s{insert})")
        r = PerformanceResult(None, -1)
        ex:Exception | None = None
        try:
            def performance(func:Callable[[], Any]) ->  PerformanceResult:
                """
                funcを実行した時間を計測
                """
                import time
                start = time.perf_counter() 
                r = func()
                return PerformanceResult(r, time.perf_counter()-start)
            save_wav(record, index, data, mic.sample_rate)
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
            if r.result not in ["", " ", "\n", None]:
                logger.notice(f"認識時間[{round(r.time, 2)}s],PCM[{round(pcm_sec, 2)}s],{round(r.time/pcm_sec, 2)}tps", end=": ")
                outputer.output(r.result[0])
            if not r.result[1] is None:
                logger.debug(f"{r.result[1]}")
        except recognition.TranscribeException as e:
            ex = e
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
                        logger.debug(f"#{e.message}\r\n{raw}")
                else:
                    logger.debug(f"#{e.message}")
                    logger.debug(f"#{type(e.inner)}:{e.inner}")
        except output.WsOutputException as e:
            ex = e
            logger.info(e.message)
            if not e.inner is None:
                logger.debug(f"# => {type(e.inner)}:{e.inner}")
        except Exception as e:
            ex = e
            logger.print(f"!!!!意図しない例外({type(e)}:{e})!!!!")
            logger.print(traceback.format_exc())
        for it in [("", mic.get_verbose(env.verbose)), ("", recognition_model.get_verbose(env.verbose))]:
            pass
        logger.debug(f"#認識処理終了(#{index}, time={dt.datetime.now()})")

        # ログ出力
        try:
            log_transcribe:str
            log_time = " - "
            log_exception = " - "
            log_insert:str
            if not r.result is None:
                log_transcribe = " - "
                if r.result[0] not in ["", " ", "\n", None]:
                    log_transcribe = r.result[0]
                if not r.result[1] is None:
                    log_transcribe = f"{log_transcribe}\n{r.result[1]}"
                log_time = f"{round(r.time, 2)}s {round(r.time/1000.0/pcm_sec, 2)}tps"
            if not ex is None:
                log_transcribe = " -失敗- "
                log_exception = f"{type(ex)}"
                if isinstance(ex, src.exception.IlluminateException):
                    log_exception = f"{log_exception}:{ex.message}\ninner = {type(ex.inner)}:{ex.inner}"
                else:
                    log_exception = f"{log_exception}:{ex}"
                if isinstance(ex, recognition.TranscribeException):
                    pass
            if 0 < mic.end_insert_sec:
                log_insert = f"({round(mic.end_insert_sec, 2)}s挿入)"
            else:
                log_insert = ""
            if not param.energy is None:
                log_insert = f"{log_insert}, energy={round(param.energy, 2)}"

            logger.log([
                f"認識処理:#{index}",
                f"録音情報:{round(pcm_sec, 2)}s{log_insert}, {(int)(len(data)/2)}sample / {mic.sample_rate}Hz",
                f"認識結果:{log_transcribe}",
                f"認識時間:{log_time}",
                f"例外情報:{log_exception}",
                f"マイク情報: {mic.get_log_info()}",
                f"認識モデル情報: {recognition_model.get_log_info()}",
            ])
        except Exception as e_: # eにするとPylanceの動きがおかしくなるので名前かえとく
            logger.print(f"!!!!ログ出力例外({type(e_)}:{e_})!!!!")
            logger.print(traceback.format_exc())

    def onrecord_async(index:int, data:src.mic.ListenResult) -> None:
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

def is_feature(feature:str, func:str) -> bool:
    """
    featureにfuncが含まれるか判定
    """
    def strip(s:str) -> str:
        return str.strip(s)
    return func in map(strip, feature.split(","))


def save_wav(record:Record, index:int, data:bytes, sampling_rate) -> None:
    """
    音声データをwavに保存
    """
    if record.is_record:
        with open(f"{record.directory}{os.sep}{record.file}-{str(index).zfill(4)}.wav", "wb") as fout:      
            fout.write(speech_recognition.AudioData(data, sampling_rate, 2).get_wav_data())

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    main() # type: ignore
