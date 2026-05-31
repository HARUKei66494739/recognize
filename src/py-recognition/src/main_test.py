import os
import sys
import platform
import traceback
import audioop
import numpy as np
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Iterable, Optional, NamedTuple


from src import Logger, db2rms, rms2db
import src.microphone
import src.val as val
import src.exception
import src.output as output
from src.main_common import Record, save_wav
from src.cancellation import CancellationObject

def run_mic(
    mic:src.microphone.Microphone,
    rec:Record,
    logger:Logger,
    cancel:CancellationObject, _:str) -> None:
    """
    マイクテスト
    """
    def onend(index:int, param:str|src.microphone.ListenResultParam|None) -> None:
        """
        マイク認識結果が返るコールバック関数
        """
        def energy(v:float|None) -> float: return v if not v is None else -1.
        if param is None:
            # 認識しなかった場合今のところ何もしない
            return

        if isinstance(param, str):
            return

        sec = len(param.pcm) / 2 / mic.sample_rate

        logger.print("認識終了")
        logger.print(f"{round(sec - mic.end_insert_sec, 2)}[秒]発声を認識しました")
        if not param.energy is None:
            logger.print(f"入力　　　 : {rms2db(param.energy.value):.2f}dB")
        logger.print(" ")

        logger.log([
            f"認識 #{str(index).zfill(2)}",
            f"PCM    = {round(sec - mic.end_insert_sec, 2)}sec",
            f"dB     = {(rms2db(param.energy.value) if not param.energy is None else 0):.2f}",
            f"energy = {(param.energy.value if not param.energy is None else 0):.2f}"
        ])
        save_wav(rec, index, param.pcm, mic.sample_rate, 2, logger)

    logger.log([
        "マイクテスト起動"
        f"マイク: {mic.device_name}",
    ])

    logger.print("マイクテストを行います")
    logger.print(f"マイクを監視し声を拾った場合その旨を表示します")
    logger.print(f"使用マイク　　　　　　 : {mic.device_name}")
    logger.print("終了する場合はctr+cを押してください")
    logger.print("")
    mic.listen(
        onend,
        cancel,
        opt_enable_indicator = True)
    return


def run_ambient(
    mic:src.microphone.DeviceMicrophone,
    timeout:float,
    logger:Logger,
    _:str) -> None:

    import speech_recognition as sr
    import math
    import re
    repatter = re.compile("^.+\\.0$")
    def fmt(txt:str, padding:int) -> str:
        text_len = len(txt)
        pad = padding - text_len #+ ((text_len % 2 - 1) * -1)
        return txt + "".ljust(max(0, pad), "　")
    def value(v:float|None, default:float) -> float: return v if not v is None else default
    def calc_threshold(energy:float|Iterable[float], threshold:float) -> float:
        if isinstance(energy, Iterable):
            return sum(energy) / len(list(energy)) * 1.2
        else:
            return energy * 1.2

    def add(lst:list[float], v:tuple[float, list[float]], max:int) -> None:
        lst.append(v[0])
        if max <= len(lst):
            lst.pop(1)

    def avg(lst:list[float]) -> float:
        return sum(lst) / len(lst)

    def round_s(f:float) -> str:
        '''
        round(f, 2) の結果がN.0の場合 str(int(f)) とし末尾小数点を付与しない形に成形する
        '''
        def r():
            s = str(round(f, 2))
            if repatter.match(s) is None:
                return s
            else:
                return str(int(f))
        t = r()
        return r().rjust(len(t) % 2)

    max_list:int = max(math.ceil(60 / timeout), 10) # 1分サンプル/最低10レコード保障 

    logger.log("環境音測定機能を起動")
    logger.print("環境音の測定を行います")
    logger.print("発言はせず、実際に利用する際にとる行動をおこなってください。")
    logger.print(f"この機能は次の3種の音圧を取り扱います。")
    logger.print(f"A. {round_s(timeout)}[秒]おきに表示する直近の音圧")
    logger.print(f"B. 中期間M[分]保存した音圧")
    logger.print(f"C. (A.)で計測した音圧の最大値と最小値")
    logger.print(f" ")
    logger.print(f"そして音圧閾値を提案します。")
    logger.print(f"A. 計測期間中更新し続ける今使うのに適している閾値")
    logger.print(f"B. 初期閾値から{round_s(timeout * max_list / 60)}[分]の音圧平均で求められる閾値")
    logger.print(f"C. 初期閾値と計測中最大/最小を記録した音圧で求められる閾値")
    logger.print(" ")
    logger.print("終了は ctrl+c を押してください。")
    try:
        list_energys:list[float] = []
        energy_max:tuple[float, list[float]] = (-1, [])
        energy_min:tuple[float, list[float]] = (-1, [])
        while True:
            energy_history:list[float] = []

            logger.print(f"{round_s(timeout)}[秒]マイクから環境音を採取します")
            logger.print(f"マイク情報　　 : {mic.device_name}, {mic.sample_rate}[Hz]/{mic.sample_width * 8}[bit]")
            logger.print(f"サイクル標本量 : {mic.chunk_size}[sample]")

            ret = mic.listen_ambient(timeout)

            energy_history.append(ret.value)
            energy_avg = (sum(energy_history)/len(energy_history), energy_history)
            energy_threshold = calc_threshold(energy_history, 0)
            add(list_energys, energy_avg, max_list)
            energy_max = max(energy_max, energy_avg, key=lambda x: x[0])
            energy_min = min(energy_min, energy_avg, key=lambda x: x[0]) if 0 <= energy_min[0] else energy_avg
            recernt_energy_avg = avg(list_energys)
            logger.print("完了")

            # ここから結果表示用の計算と主にフォーマット処理
            format_length = 10
            sep_length = 80
            s_energy_avg = f"{rms2db(energy_avg[0]):.2f}"
            s_energy_threshold = f"{rms2db(energy_threshold):.2f}"
            s_energy_max = f"{rms2db(energy_max[0]):.2f}"
            s_energy_min = f"{rms2db(energy_min[0]):.2f}"
            s_recernt_energy_avg = f"{rms2db(recernt_energy_avg):.2f}"
            en_length = max(
                len("value"),
                len(s_energy_avg),
                len(s_energy_max),
                len(s_energy_min),
                len(s_recernt_energy_avg)
            )
            s_th_max = f"{rms2db(calc_threshold(energy_max[1], mic.energy_threshold)):.2f}"
            s_th_min = f"{rms2db(calc_threshold(energy_min[1], mic.energy_threshold)):.2f}"
            s_recernt_th = f"{rms2db(calc_threshold(list_energys, mic.energy_threshold)):.2f}"
            th_length = max(
                len("threshold"),
                len(s_energy_threshold),
                len(s_th_max),
                len(s_th_min),
                len(s_recernt_th)
            )
            out = [
                "".ljust(sep_length, "-"),
                fmt(f"", format_length) + "  " + "value".rjust(en_length) + ", " + "threshold".rjust(th_length),
                "".ljust(sep_length, "-"),
                fmt(f"計測音圧", format_length) + f": {s_energy_avg.rjust(en_length)}, {s_energy_threshold.rjust(th_length)}",
                "".ljust(sep_length, "-"),
                fmt(f"計測中最大の音圧", format_length) +  f": {s_energy_max.rjust(en_length)}, {s_th_max.rjust(th_length)}",
                fmt(f"計測中最小の音圧", format_length) +  f": {s_energy_min.rjust(en_length)}, {s_th_min.rjust(th_length)}",
                fmt(f"直近を平均した音圧", format_length) + f": {s_recernt_energy_avg.rjust(en_length)}, {s_recernt_th.rjust(th_length)}",
                "".ljust(sep_length, "-"),
            ]
            logger.print(os.linesep.join(out))
            out.append(os.linesep.join([
                "RAW DATA",
                "計測" + f"{energy_avg[0]:.2f}, {energy_threshold:.2f}",
                "最大" + f"{energy_max[0]:.2f}, {calc_threshold(energy_max[1], mic.energy_threshold):.2f}",
                "最低" + f"{energy_min[0]:.2f}, {calc_threshold(energy_min[1], mic.energy_threshold):.2f}",
                "平均" + f"{recernt_energy_avg:.2f}, {calc_threshold(list_energys, mic.energy_threshold):.2f}",
            ]))
            logger.log(out)
            logger.print(" ")
    except Exception as e:
        logger.error([
            f"!!!!意図しない例外({type(e)}:{e})!!!!",
            f"{type(e)}:{e}",
            traceback.format_exc()
        ])

def run_illuminate(
    out:output.IlluminateSpeechOutputer,
    logger:Logger,
    _:str) -> None:


    logger.log("illuminateテスト機能を起動")
    logger.print("入力した行を送信します。")
    logger.print("終了は ctrl+c を押してください。")
    while True:
        out.output(input(), "")
