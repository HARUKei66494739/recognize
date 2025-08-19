#!/usr/bin/env python3

import os
import sys
import platform
import click
import importlib.util
import json
from typing import Any, Callable, Iterable, Optional, NamedTuple

from src import Logger, Enviroment, db2rms, rms2db, ilm_logger, mm_atach, mm_is_capture_device
import src.main_run as main_run
import src.main_test as main_test
import src.filter_transcribe as filter_t
import src.recognition as recognition
import src.recognition_translate as translate_
import src.output as output
import src.output_subtitle as output_subtitle
import src.microphone as microphone
import src.val as val
import src.google_recognizers as google
import src.exception
from src.main_common import Record
from src.cancellation import CancellationObject
import src.filter as filter

def select_google_tcp(ctx, param, value):
    import src.google_recognizers as google
    if not value or ctx.resilient_parsing:
        return
    
    if value == "urllib":
        ilm_logger.log(f"google tcpは{value}で接続")
        google.recognize_google = google.recognize_google_urllib
        google.recognize_google_duplex = google.recognize_google_duplex_urllib
    elif value == "requests":
        ilm_logger.log(f"google tcpは{value}で接続")
        google.recognize_google = google.recognize_google_requests
        google.recognize_google_duplex = google.recognize_google_duplex_requests
    else:
        ilm_logger.error(f"unknown option-value: {value}")


def print_mics(ctx, param, value):
    """
    マイク情報出力
    """
    from src import ilm_logger

    if not value or ctx.resilient_parsing:
        return
    for mic in microphone.Microphone.query_devices():
         ilm_logger.print(mic)
    ctx.exit()
    return

def __available_cuda() -> str:
    if importlib.util.find_spec("torch") is None:
        return "cpu"
    else:
        return "cuda" if val.SUPPORT_CUDA else "cpu"

def __whiper_help(s:str) -> str:
    if not val.SUPPORT_WHISPER:
        return "サポートしていません"
    return s

@click.command()
@click.option("--test", default="", help="テストを行います",type=click.Choice(val.ARG_CHOICE_TEST))

@click.option("--method", default=val.DEFALUT_METHOD_VALUE, help="使用する認識方法", type=click.Choice(val.ARG_CHOICE_METHOD))
@click.option("--whisper_model", default="medium", help=__whiper_help("(whisper)使用する推論モデル"), type=str) # type=click.Choice(["tiny","base", "small","medium","large","large-v2","large-v3"])
@click.option("--whisper_device", default=__available_cuda(), help=__whiper_help("(whisper)使用する演算装置"), type=click.Choice(["cpu","cuda"]))
@click.option("--whisper_device_index", default=0, help=__whiper_help("(whisper)使用するデバイスindex"), type=int)
@click.option("--whisper_language", default="", help=__whiper_help("(whisper)音声解析対象の言語"), type=click.Choice(val.LANGUAGE_CODES))
@click.option("--google_language", default="ja-JP", help="(google)音声解析対象の言語", type=str)
@click.option("--google_timeout", default=5.0, help="(google)最大認識待ち時間", type=float)
@click.option("--google_convert_sampling_rate", default=False, help="(google)マイク入力を16kに変換します", is_flag=True, type=bool)
@click.option("--google_error_retry", default=1, help="(google)500エラー時にリトライ試行する回数", type=int)
@click.option("--google_profanity_filter", default=False, help="(google)冒とくフィルタを有効にします", is_flag=True, type=bool)
@click.option("--google_duplex_parallel", default=False, help="(google_duplexのみ)複数並列リクエストを投げエラーの抑制を図ります", is_flag=True, type=bool)
@click.option("--google_duplex_parallel_max", default=None, help="(google_duplexのみ)複数並列リクエスト数増減時の最大並列数", type=int)
@click.option("--google_duplex_parallel_reduce_count", default=None, help="(google_duplexのみ)増加した並列数を減少するために必要な成功数", type=int)
@click.option("--google_tcp", default=None, help="-", type=click.Choice(["urllib", "requests"]), callback=select_google_tcp, expose_value=False, is_eager=True)

@click.option("--transcribe_filter", default=None, help="変換フィルタルールファイル", type=str)

@click.option("--translate", default="", help="使用する翻訳方法", type=click.Choice(val.ARG_CHOICE_TRANSLATE))
@click.option("--translate_whisper_device", default=__available_cuda(), help=__whiper_help("(whisper)翻訳に使用する演算装置"), type=click.Choice(["cpu","cuda"]))
@click.option("--translate_whisper_device_index", default=0, help=__whiper_help("(whisper)翻訳に使用するデバイスindex"), type=int)

@click.option("--mic", default=None, help="使用するマイクのindex", type=int)
@click.option("--mic_name", default=None, help="マイクの名前を部分一致で検索します。--micが指定されている場合この指定は無視されます", type=str)
#@click.option("--mic_api", default=val.MIC_API_VALUE_MME, help="--mic_nameで検索するマイクのAPIを指定します", type=click.Choice(val.ARG_CHOICE_MIC_API))
@click.option("--mic_energy_threshold", default=None, help="互換性のため残されています", type=float)
@click.option("--mic_db_threshold", default=0, help="設定した値より小さい音を無言として扱う閾値", type=float)
@click.option("--mic_pause_duration", default=0.8, help="声認識後VADにかけていいく塊の秒数", type=float)
@click.option("--mic_record_min_duration", default=0.0, help="マイクの入力がこの値より短い場合無視する秒数", type=float)
#@click.option("--mic_sampling_rate", default=16000, help="-", type=int)
@click.option("--mic_head_insert_duration", default=None, help="-", type=float)
@click.option("--mic_tail_insert_duration", default=None, help="-", type=float)
@click.option("--mic_push_talk", default=None, help="マイクをプッシュトゥトークで使用するための監視パラメータ", type=str, multiple=True)


@click.option("--out", default=val.OUT_VALUE_PRINT, help="認識結果の出力先", type=click.Choice(val.ARG_CHOICE_OUT), multiple=True)
@click.option("--out_yukarinette",default=49513, help="ゆかりねっとの外部連携ポートを指定", type=int)
@click.option("--out_yukacone",default=None, help="ゆかコネNEOの外部連携ポートを指定", type=int)
@click.option("--out_illuminate_exe",default="", help="-", type=str)
@click.option("--out_illuminate_voice",default="voiceroid", help="-", type=click.Choice(["voiceroid", "voiceroid2", "voicepeak", "aivoice", "aivoice2"]))
@click.option("--out_illuminate_client",default="", help="-", type=str)
@click.option("--out_illuminate_launch",default=False, help="-", type=str)
@click.option("--out_illuminate_port",default=49514, help="-",type=int)
@click.option("--out_illuminate_notify_icon",default=False, help="-",type=bool, is_flag=True)
@click.option("--out_illuminate_debug",default=False, help="-",type=bool, is_flag=True)
@click.option("--out_illuminate_kana",default=False, help="-",type=bool, is_flag=True)
@click.option("--out_illuminate_capture_pause",default=1.0, help="-",type=float)
@click.option("--out_file_truncate", default=4.0, help="字幕を消去する時間(秒)", type=float)
@click.option("--out_file_directory", default=None, help="ファイル字幕連携で保存先", type=str)
@click.option("--out_obs_truncate", default=4.0, help="字幕を消去する時間(秒)", type=float)
@click.option("--out_obs_host", default="localhost", help="", type=str)
@click.option("--out_obs_port", default=4455, help="OBS Web Socket APIのポート", type=int)
@click.option("--out_obs_password", default="", help="OBS Web Socket APIのパスワード", type=str)
@click.option("--out_obs_text_ja", default=None, help="字幕(ja_JP)テキストオブジェクトの名前", type=str)
@click.option("--out_obs_text_en", default=None, help="字幕(en_US)テキストオブジェクトの名前", type=str)

@click.option("--filter_hpf", default=None, help="ハイパスフィルタのカットオフ周波数を設定、ハイパスフィルタを有効化", type=int)

@click.option("--vad", default=val.VAD_VALUE_GOOGLE, help="VADエンジンの選択", type=click.Choice(val.ARG_CHOICE_VAD))
@click.option("--vad_google_mode", default="0", help="VADの強度",type=click.Choice(["0", "1", "2", "3"]))
@click.option("--vad_silero_threshold", default=0.5, help="-",type=float)
@click.option("--vad_silero_min_speech_duration", default=0.25, help="-",type=float)

@click.option("--print_mics", help="マイクデバイスの一覧をプリント", is_flag=True, callback=print_mics, expose_value=False, is_eager=True)

@click.option(val.ARG_NAME_VERBOSE, default=val.ARG_DEFAULT_VERBOSE, help="出力ログレベルを指定", type=click.Choice(val.ARG_CHOICE_VERBOSE))
@click.option(val.ARG_NAME_LOG_FILE, default=val.ARG_DEFAULT_LOG_FILE, help="ログファイルの出力ファイル名を指定します", type=str)
@click.option(val.ARG_NAME_LOG_DIRECTORY, default=val.ARG_DEFAULT_LOG_DIRECTORY, help="ログ格納先のディレクトリを指定します", type=str)
@click.option(val.ARG_NAME_LOG_ROTATE, default=False, help="-", is_flag=True, type=bool)
@click.option("--record",default=False, help="録音した音声をファイルとして出力します", is_flag=True, type=bool)
@click.option("--record_file", default="record", help="録音データの出力ファイル名を指定します", type=str)
@click.option("--record_directory", default=None, help="録音データの出力先ディレクトリを指定します", type=str)

@click.option("--torch_cache", default="", help="torchがダウンロードするキャッシュの場所を指定します", type=str)
@click.option("--feature", default="", help="-", type=str)
@click.option("--ftr_transcribe_file", default="", help="-", type=str)
def main(
    test:str,
    method:str,
    whisper_model:str,
    whisper_device:str,
    whisper_device_index:int,
    whisper_language:str,
    google_language:str,
    google_timeout:float,
    google_convert_sampling_rate:bool,
    google_error_retry:int,
    google_profanity_filter:bool,
    google_duplex_parallel:bool,
    google_duplex_parallel_max:Optional[int],
    google_duplex_parallel_reduce_count:Optional[int],
    transcribe_filter:Optional[str],
    translate:str,
    translate_whisper_device:str,
    translate_whisper_device_index:int,

    mic:Optional[int],
    mic_name:Optional[str],
    #mic_api:str,

    mic_energy_threshold:Optional[float],
    mic_db_threshold:float,
    mic_pause_duration:float,
    mic_record_min_duration:float,
    mic_head_insert_duration:Optional[float],
    mic_tail_insert_duration:Optional[float],
    mic_push_talk:list[str],

    out:list[str],
    out_yukarinette:int,
    out_yukacone:Optional[int],
    out_illuminate_exe:str,
    out_illuminate_voice:str,
    out_illuminate_client:str,
    out_illuminate_launch:bool,
    out_illuminate_port:int,
    out_illuminate_notify_icon:bool,
    out_illuminate_kana:bool,
    out_illuminate_debug:bool,
    out_illuminate_capture_pause:float,
    out_file_truncate:float,
    out_file_directory:str,
    out_obs_truncate:float,
    out_obs_host:str,
    out_obs_port:int,
    out_obs_password:str,
    out_obs_text_ja:Optional[str],
    out_obs_text_en:Optional[str],

    filter_hpf:Optional[int],
    vad:str,
    vad_google_mode:str,
    vad_silero_threshold:float,
    vad_silero_min_speech_duration:float,
    verbose:str,
    log_file:str,
    log_directory:Optional[str],
    log_rotate:bool,
    record:bool,
    record_file:str,
    record_directory:Optional[str],

    torch_cache:str,
    feature:str,
    ftr_transcribe_file:str
    ) -> None:
    from src import ilm_logger, ilm_enviroment, enable_virtual_terminal

    if enable_virtual_terminal() != True:
        ilm_logger.error("仮想ターミナルの設定に失敗しました")

    # torch/kotoba-whisperのダウンロード設定をする(torchのimport前に実施)
    if torch_cache == "" or torch_cache == None:
        os.environ["TORCH_HOME"] = \
            os.environ["HUGGINGFACE_HUB_CACHE"] = \
                f"{ilm_enviroment.root}{os.sep}.cache"
    else:
        os.environ["TORCH_HOME"] = \
            os.environ["HUGGINGFACE_HUB_CACHE"] = \
                f"{torch_cache}{os.sep}.cache"     

    if out_illuminate_exe == "":
        out_illuminate_exe = "" 

    cancel = CancellationObject()
    try:
        if record_directory is None:
            record_directory = ilm_enviroment.root
        else:
            os.makedirs(record_directory, exist_ok=True)

        if out_file_directory  is None:
            out_file_directory = ilm_enviroment.root
        else:
            os.makedirs(out_file_directory, exist_ok=True)

        if test == val.TEST_VALUE_ILLUMINATE:
            main_test.run_illuminate(
                output.IlluminateSpeechOutputer(
                    "localhost",
                    out_illuminate_port,
                    out_illuminate_exe,
                    out_illuminate_voice,
                    out_illuminate_client,
                    out_illuminate_launch,
                    out_illuminate_kana,
                    out_illuminate_notify_icon,
                    out_illuminate_debug,
                    out_illuminate_capture_pause,
                    cancel),
                ilm_logger,
                feature)

        print("\033[?25l", end="") # カーソルを消す

        if 0 < len(mic_push_talk):
            for it in mic_push_talk:
                v, _ = it.split(":")
                v = v.lower()
                if (v == "vr") or (v == "index") or (v == "quest"):
                    ilm_logger.info("VR連携の初期化")
                    import src.vr
                    src.vr.init()
                    break

        #sampling_rate = src.mic.Mic.update_sample_rate(mic, mic_sampling_rate) #16000
        sampling_rate = 16000
        rec = Record(record, record_file, record_directory)

        # マイクにフィルタを渡すので先に用意
        filter_highPass:filter.NoiseFilter | None = None
        filters = []
        if not filter_hpf is None:
            filter_highPass = filter.HighPassFilter(
                sampling_rate,
                filter_hpf)
            filters.append(filter_highPass)
        # VADフィルタの準備
        filter_vad_inst:filter.VoiceActivityDetectorFilter
        if vad == val.VAD_VALUE_GOOGLE:
            filter_vad_inst = filter.GoogleVadFilter(
                val.MIC_SAMPLE_RATE,
                int(vad_google_mode))
        elif vad == val.VAD_VALUE_SILERO:
            import src.filter_torch as fil_torch
            filter_vad_inst = fil_torch.SileroVadFilter(
                val.MIC_SAMPLE_RATE,
                vad_silero_threshold,
                vad_silero_min_speech_duration)
        else:
            raise ValueError(f"vad:{vad} is not support")
        filters.append(filter_vad_inst)

        ilm_logger.print("マイクの初期化")
        mp_recog_conf:recognition.RecognizeMicrophoneConfig = {
            val.METHOD_VALUE_WHISPER: lambda: recognition.WhisperMicrophoneConfig(mic_head_insert_duration, mic_tail_insert_duration),
            val.METHOD_VALUE_WHISPER_FASTER: lambda: recognition.WhisperMicrophoneConfig(mic_head_insert_duration, mic_tail_insert_duration),
            val.METHOD_VALUE_WHISPER_KOTOBA: lambda: recognition.WhisperMicrophoneConfig(mic_head_insert_duration, mic_tail_insert_duration),
            #val.METHOD_VALUE_WHISPER_KOTOBA_BIL: lambda: recognition.WhisperMicrophoneConfig(mic_head_insert_duration, mic_tail_insert_duration),
            val.METHOD_VALUE_GOOGLE: lambda: recognition.GoogleMicrophoneConfig(mic_head_insert_duration, mic_tail_insert_duration),
            val.METHOD_VALUE_GOOGLE_DUPLEX: lambda: recognition.GoogleMicrophoneConfig(mic_head_insert_duration, mic_tail_insert_duration),
            val.METHOD_VALUE_GOOGLE_MIX: lambda: recognition.GoogleMicrophoneConfig(mic_head_insert_duration, mic_tail_insert_duration),
        }[method]()

        def mp_value(db, en): return db if en is None else en
        mp_energy = mp_value(db2rms(mic_db_threshold), mic_energy_threshold)
        mp_mic = mic
        if mp_mic is None and (not mic_name is None) and mic_name != "":
            for d in microphone.Microphone.query_devices():
                if(mic_name.lower() in d.name.lower()):
                    mp_mic = d.device_no
                    break
            if mp_mic is None:
                ilm_logger.info(f"マイク[{mic_name}]を検索しましたが見つかりませんでした", console=val.Console.Red, reset_console=True)
                ilm_logger.log("query_devices() microphone not found")

        mc = microphone.Microphone(
            mp_energy,
            mp_recog_conf,
            filter_vad_inst,
            filter_highPass,
            mic_pause_duration,
            mic_record_min_duration,
            mic_push_talk,
            mp_mic,
            ilm_logger)
        ilm_logger.print(f"マイクは{mc.device_name}を使用します")

        if test == val.TEST_VALUE_MIC:
            main_test.run_mic(
                mc,
                rec,
                ilm_logger,
                cancel,
                feature)
        elif test == val.TEST_VALUE_AMBIENT:
            main_test.run_ambient(
                mc,
                3.0,
                ilm_logger,
                feature)
        else:
            is_loaded_torch = False

            ilm_logger.print("認識モデルの初期化")
            if method in [val.METHOD_VALUE_WHISPER, val.METHOD_VALUE_WHISPER_FASTER, val.METHOD_VALUE_WHISPER_KOTOBA]:
                if not is_loaded_torch:
                    ilm_logger.print("torchをロードします。この処理は時間がかかることがあります", console=val.Console.Yellow, reset_console=True)
                    is_loaded_torch = True

                import src.recognition_torch as recognition_torch
                recognition_model:recognition.RecognitionModel = {
                    val.METHOD_VALUE_WHISPER: lambda: recognition_torch.RecognitionModelWhisper(
                        model=whisper_model,
                        language=whisper_language,
                        device=whisper_device,
                        download_root=f"{ilm_enviroment.root}{os.sep}.cache"),
                    val.METHOD_VALUE_WHISPER_FASTER: lambda:  recognition_torch.RecognitionModelWhisperFaster(
                        model=whisper_model,
                        language=whisper_language,
                        device=whisper_device,
                        device_index=whisper_device_index,
                        download_root=f"{ilm_enviroment.root}{os.sep}.cache"),
                    val.METHOD_VALUE_WHISPER_KOTOBA: lambda: recognition_torch.RecognizeAndTranslateModelKotobaWhisper(
                        device=whisper_device,
                        device_index=whisper_device_index),
                }[method]()
            else:
                recognition_model:recognition.RecognitionModel = {
                    val.METHOD_VALUE_GOOGLE: lambda: recognition.RecognitionModelGoogle(
                        sample_rate=sampling_rate,
                        sample_width=2,
                        convert_sample_rete=google_convert_sampling_rate,
                        language=google_language,
                        profanity_filter=google_profanity_filter,
                        timeout=google_timeout if 0 < google_timeout else None,
                        challenge=google_error_retry),
                    val.METHOD_VALUE_GOOGLE_DUPLEX: lambda: recognition.RecognitionModelGoogleDuplex(
                        sample_rate=sampling_rate,
                        sample_width=2,
                        convert_sample_rete=google_convert_sampling_rate,
                        language=google_language,
                        profanity_filter=google_profanity_filter,
                        timeout=google_timeout if 0 < google_timeout else None,
                        challenge=google_error_retry,
                        is_parallel_run=google_duplex_parallel,
                        parallel_max=google_duplex_parallel_max,
                        parallel_reduce_count=google_duplex_parallel_reduce_count),
                    val.METHOD_VALUE_GOOGLE_MIX: lambda: recognition.RecognitionModelGoogleMix(
                        sample_rate=sampling_rate,
                        sample_width=2,
                        convert_sample_rete=google_convert_sampling_rate,
                        language=google_language,
                        profanity_filter=google_profanity_filter,
                        timeout=google_timeout if 0 < google_timeout else None,
                        challenge=google_error_retry,
                        parallel_max_duplex=google_duplex_parallel_max,
                        parallel_reduce_count_duplex=google_duplex_parallel_reduce_count),
                }[method]()
            ilm_logger.debug(f"#認識モデルは{type(recognition_model)}を使用", reset_console=True)

            if translate == "":
                translate_model:None|translate_.TranslateModel = None
            else:
                ilm_logger.print("翻訳モデルの初期化")
                if translate == method:
                    assert(isinstance(recognition_model, translate_.TranslateModel))
                    translate_model = recognition_model
                else:
                    if not is_loaded_torch:
                        ilm_logger.print("torchをロードします。この処理は時間がかかることがあります", console=val.Console.Yellow, reset_console=True)
                        is_loaded_torch = True
                    import src.recognition_torch as recognition_torch
                    translate_model = {
                        val.METHOD_VALUE_WHISPER_KOTOBA: lambda: recognition_torch.RecognizeAndTranslateModelKotobaWhisper(
                            device=translate_whisper_device,
                            device_index=translate_whisper_device_index),
                    }[translate]()
                ilm_logger.debug(f"#翻訳モデルは{type(translate_model)}を使用", reset_console=True)

            ilm_logger.print("出力モデルの初期化")
            outputers:list[output.RecognitionOutputer] = []
            illuminate:output.IlluminateSpeechOutputer|None = None
            outputer_map = {
                #val.OUT_VALUE_PRINT: lambda: output.PrintOutputer(),
                val.OUT_VALUE_YUKARINETTE: lambda: output.YukarinetteOutputer(
                    f"ws://localhost:{out_yukarinette}"),
                val.OUT_VALUE_YUKACONE: lambda: output.YukaconeOutputer(
                    f"ws://localhost:{output.YukaconeOutputer.get_port(out_yukacone)}"),
                val.OUT_VALUE_ILLUMINATE: lambda: output.IlluminateSpeechOutputer(
                    "localhost",
                    out_illuminate_port,
                    out_illuminate_exe,
                    out_illuminate_voice,
                    out_illuminate_client,
                    out_illuminate_launch,
                    out_illuminate_notify_icon,
                    out_illuminate_kana,
                    out_illuminate_debug,
                    out_illuminate_capture_pause,
                    cancel),
                val.OUT_VALUE_OBS: lambda: output_subtitle.ObsV5SubtitleOutputer(
                    out_obs_host,
                    out_obs_port,
                    out_obs_password,
                    out_obs_text_ja,
                    out_obs_text_en,
                    out_obs_truncate,
                    ilm_logger),
                val.OUT_VALUE_FILE: lambda: output_subtitle.FileSubtitleOutputer(
                    out_file_directory,
                    out_file_truncate,
                    ilm_logger),
                val.OUT_VALUE_VRC: lambda: output.VrChatOutputer()
            }
            outputers.append(output.PrintOutputer())
            for it in out:
                if it in outputer_map:
                    o = outputer_map[it]()
                    outputers.append(o)
                    if isinstance(o, output.IlluminateSpeechOutputer):
                        illuminate = o
            if illuminate != None:
                ilm_logger.print("illuminate同期の設定")

                sbtl:list[output.RecognitionOutputer] = []
                for it in outputers:
                    if isinstance(it, output_subtitle.SubtitleOutputer):
                        sbtl.append(it)
                if 0 < len(sbtl):
                    for it in sbtl:
                        outputers.remove(it)
                    illuminate.set_subtitle_cooperation(sbtl)
                ilm_logger.debug(f"#出力は{','.join(list(map(lambda x: f'{type(x)}', outputers)))}を使用", reset_console=True)
                ilm_logger.debug(f"#illuminate同期は{','.join(list(map(lambda x: f'{type(x)}', sbtl)))}を使用", reset_console=True)
            else:
                ilm_logger.debug(f"#出力は{','.join(list(map(lambda x: f'{type(x)}', outputers)))}を使用", reset_console=True)

            ilm_logger.debug(f"#使用音声フィルタ({len(filters)}):", reset_console=True)
            for f in filters:
               ilm_logger.debug(f"#{type(f)}", reset_console=True)

            jsn = {}
            if transcribe_filter is None:
                filter_transcribe = filter_t.TranscribeFilter(None)
            else:
                ilm_logger.print("認識変換フィルタ読み込み")
                with open(transcribe_filter, "r", encoding="utf-8") as json_file:
                    try:
                        jsn = json.load(json_file)
                        filter_transcribe = filter_t.TranscribeFilter(jsn)
                    except json.decoder.JSONDecodeError as ex:
                        ilm_logger.error("JSONファイルの内容が不正です。読み込みをスキップします")
                        ilm_logger.error({ex})
                        filter_transcribe = filter_t.TranscribeFilter(None)
                    except filter_t.JsonReadException as ex:
                        ilm_logger.error("JSONファイルの内容が不正です。読み込みをスキップします")
                        ilm_logger.error({ex})
                        filter_transcribe = filter_t.TranscribeFilter(None)

            ilm_logger.log([
                f"マイク: {mc.device_name}",
                f"認識モデル: {type(recognition_model)}",
                f"翻訳モデル: {type(translate_model)}",
                f"出力: {','.join(list(map(lambda x: f'{type(x)}', outputers)))}",
                f"マイクフィルタ = {','.join(list(map(lambda x: f'{type(x)}', filters)))}",
                f"変換フィルタ: {str(jsn)}",
            ])

            if feature == "transcribe":
                import src.feature_transcribe
                assert(isinstance(recognition_model, recognition.RecognitionModel))
                src.feature_transcribe.run(
                    ftr_transcribe_file,
                    recognition_model,
                    ilm_enviroment,
                    ilm_logger,
                    feature)
            else:
                ilm_logger.print("認識中…")
                assert(isinstance(recognition_model, recognition.RecognitionModel))
                main_run.run(
                    mc,
                    recognition_model,
                    translate_model,
                    filter_transcribe,
                    outputers,
                    rec,
                    ilm_enviroment,
                    cancel,
                    ilm_logger,
                    feature)
    #except src.mic.MicInitializeExeception as e:
    #    ilm_logger.print(e.message)
    #    ilm_logger.print(f"{type(e.inner)}{e.inner}")
    except KeyboardInterrupt:
        cancel.cancel()
        ilm_logger.print("ctrl+c")
    finally:
        print("\033[?25h", end="") # カーソルを出す
    sys.exit()

def mm_callback1(flow, role, id, name) -> None:
    pass

def mm_callback_add(id, name) -> None:
    ilm_logger.print(f"デバイス追加:{name}({id})", console=val.Console.Blue, reset_console=True)
    ilm_logger.log(f"デバイス追加:{name}({id})")

def mm_callback_remove(id, name) -> None:
    ilm_logger.print(f"デバイス削除:{name}({id})", console=val.Console.Blue, reset_console=True)
    ilm_logger.log(f"デバイス削除:{name}({id})")

def mm_callback_state(id, state, name) -> None:
    DEVICE_STATE_ACTIVE = 1
    DEVICE_STATE_DISABLED = 2
    DEVICE_STATE_NOTPRESENT = 4
    DEVICE_STATE_UNPLUGGED = 8
    state_str = "-不明-"
    if state == DEVICE_STATE_ACTIVE:
        state_str = "ACTIVE"
    elif state == DEVICE_STATE_DISABLED:
        state_str = "DISABLED"
    elif state == DEVICE_STATE_NOTPRESENT:
        state_str = "NOTPRESENT"
    elif state == DEVICE_STATE_UNPLUGGED:
        state_str = DEVICE_STATE_UNPLUGGED
    ilm_logger.print(f"{name}の構成が変更されました({state_str})", console=val.Console.Blue, reset_console=True)
    ilm_logger.log(f"デバイスの構成変更:{name}({id})->{state_str}({state})")
 
if __name__ == "__main__":
    from src import ilm_logger

    ilm_logger.log([
        "起動",
        f"platform = {platform.platform()}",
        f"python = {sys.version}",
        f"arg = {sys.argv}",
    ])
    mm_atach(mm_callback1, mm_callback_add, mm_callback_remove, mm_callback_state)

    main() # type: ignore
