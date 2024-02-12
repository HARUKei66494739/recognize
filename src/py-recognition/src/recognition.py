import os
import time
import math
import torch
import whisper
import faster_whisper as fwis
import numpy as np
import speech_recognition as sr
import urllib.error as urlerr
import requests.exceptions
import concurrent.futures
from typing import Any, NamedTuple, Callable

import src.exception as ex
import src.google_recognizers as google


class TranscribeResult(NamedTuple):
    """
    RecognitionModel#transcribeの戻り値データ型
    """
    transcribe:str
    extend_data:Any

class GoogleTranscribeExtend(NamedTuple):
    """
    RecognitionModel#transcribeの戻り値データ型
    """
    raw_data:str
    retry_history:list[Exception]

    def __str__(self) -> str:
        if 0 < len(self.retry_history):
            clazz = os.linesep.join([f"{type(i)}:{i}"for i in self.retry_history])
            return f"{self.raw_data}{os.linesep}retry-stack{os.linesep}{clazz}"
        else:
            return self.raw_data

class RecognitionModel:
    """
    認識モデル抽象基底クラス
    """

    @property
    def required_sample_rate(self) -> int | None:
        ...

    def transcribe(self, _:np.ndarray) -> TranscribeResult:
        ...

class RecognitionModelWhisper(RecognitionModel):
    """
    認識モデルのwhisper実装
    """
    def __init__(
        self,
        model:str,
        language:str,
        device:str,
        download_root:str) -> None:
        self.__is_fp16 = device == "cuda"
        self.__language = language if language != "" else None

        m = f"{model}.{language}" if (model != "large") and (model != "large-v2") and (model != "large-v3") and (language == "en") else model
        self.audio_model = whisper.load_model(m, download_root=download_root).to(device)

    @property
    def required_sample_rate(self) -> int | None:
        return 16000

    def transcribe(self, audio_data:np.ndarray) -> TranscribeResult:
        r = self.audio_model.transcribe(
            torch.from_numpy(audio_data.astype(np.float32) / float(np.iinfo(np.int16).max)),
            language = self.__language,
            fp16 = self.__is_fp16)["text"]
        if isinstance(r, str):
            return TranscribeResult(r, None)
        if isinstance(r, list):
            return TranscribeResult("".join(r), None)
        raise ex.ProgramError(f"Whisper.transcribeから意図しない戻り値型:{type(r)}")

class RecognitionModelWhisperFaster(RecognitionModel):
    """
    認識モデルのfaster_whisper実装
    """
    def __init__(
        self,
        model:str,
        language:str,
        device:str,
        download_root:str) -> None:
        self.__language = language if language != "" else None

        def get(device:str) -> tuple[str, str]:
            if device == "cuda":
                try:
                    if torch.cuda.is_available():
                        mj, mi = torch.cuda.get_device_capability()
                        if 7 <= mj:
                            return ("cuda", "float16")
                        elif mj == 6 and 1 <= mi:
                            return ("cuda", "int8")
                        else:
                            return ("cpu", "int8")
                except:
                    pass
            return ("cpu", "int8")

        m = f"{model}.{language}" if (model != "large") and (model != "large-v2") and (language == "en") else model
        run_device, compute_type = get(device)
        self.audio_model = fwis.WhisperModel(
            m,
            run_device,
            compute_type = compute_type,
            download_root=download_root)

    @property
    def required_sample_rate(self) -> int | None:
        return 16000

    def transcribe(self, audio_data:np.ndarray) -> TranscribeResult:
        segments, _  = self.audio_model.transcribe(
            audio_data.astype(np.float32) / float(np.iinfo(np.int16).max),
            language = self.__language)
        c = []
        for s in segments:
            c.append(s.text)
        return TranscribeResult("".join(c), segments)

class RecognitionModelGoogleApi(RecognitionModel):
    """
    google系認識モデルの基底クラス    
    """
    def __init__(
        self,
        sample_rate:int,
        sample_width:int,
        convert_sample_rete:bool=False,
        language:str="ja-JP",
        key:str | None=None,
        timeout:float | None = None,
        challenge:int = 1):
        self.__sample_rate = sample_rate
        self.__sample_width = sample_width
        self.__max_loop = max(1, challenge)
        self.__convert_sample_rete = convert_sample_rete
        self._language = language
        self._key = key
        self._operation_timeout = timeout

    @property
    def required_sample_rate(self) -> int | None:
        return None

    def transcribe(self, audio_data:np.ndarray) -> TranscribeResult:
        flac = google.encode_falc(
            sr.AudioData(audio_data.astype(np.int16, order="C"), self.__sample_rate, self.__sample_width),
            None if not self.__convert_sample_rete else 16000)

        his = []
        loop = 0
        while loop < self.__max_loop:
            try:
                r = self._transcribe_impl(flac)
                return TranscribeResult(r.transcribe, GoogleTranscribeExtend(r.extend_data, his))
            except urlerr.HTTPError as e:
                if (e.code == 500) and (1 < self.__max_loop):
                    his.append(e)
                else:
                    raise TranscribeException("google音声認識でHTTPエラー: {}".format(e.reason), e)
            except urlerr.URLError as e:
                raise TranscribeException("google音声認識でリモート接続エラー: {}".format(e.reason), e)
            except google.HttpStatusError as e:
                if (e.status_code == 500) and (1 < self.__max_loop):
                    his.append(e)
                else:
                    raise TranscribeException("google音声認識でHTTPエラー: {}".format(e.message), e)
            except requests.exceptions.ConnectionError as e:
                raise TranscribeException("google音声認識でリモート接続エラー: {}".format(e), e)

            except google.UnknownValueError as e:
                raise TranscribeException(
                    f"googleは音声データを検出できませんでした",
                    e)

            except requests.exceptions.ReadTimeout as e:
                raise TranscribeException(f"google音声認識でリモート接続がタイムアウトしました")
                #if self.__max_loop == 1:
                #    raise TranscribeException(f"google音声認識でリモート接続がタイムアウトしました")
                #else:
                #    his.append(e)
            except TimeoutError as e:
                raise TranscribeException(f"google音声認識でリモート接続がタイムアウトしました")
                #if self.__max_loop == 1:
                #    raise TranscribeException(f"google音声認識でリモート接続がタイムアウトしました")
                #else:
                #    his.append(e)
            loop += 1
        clazz = ",".join([f"{type(i)}"for i in his])
        raise TranscribeException(f"{self.__max_loop}回試行しましたが失敗しました({clazz}])")
 
    def _transcribe_impl(self, flac:google.EncodeData) -> TranscribeResult:
        ...

class RecognitionModelGoogle(RecognitionModelGoogleApi):
    """
    認識モデルのgoogle音声認識API v2実装
    """
    def __init__(self, sample_rate: int, sample_width: int, convert_sample_rete: bool=False, language: str = "ja-JP", key: str | None = None, timeout: float | None = None, challenge: int = 1):
        super().__init__(sample_rate, sample_width, convert_sample_rete, language, key, timeout, challenge)


    def _transcribe_impl(self, flac:google.EncodeData) -> TranscribeResult:
        r = google.recognize_google(
            flac,
            self._operation_timeout,
            self._key,
            self._language,
            0)
        return TranscribeResult(r.transcript, r.raw_data)


class RecognitionModelGoogleDuplex(RecognitionModelGoogleApi):
    """
    認識モデルのgoogle全二重API実装
    """

    __MAX_PARALLEL_SUCESS = 5
    '''スレッド数を下げるために必要な平行実行の成功回数'''
    __MIN_PARALLEL = 3
    '''変動スレッド数の最低値'''
    __MAX_PARALLEL = 6
    '''変動スレッド数の最大値'''

    def __init__(
        self,
        sample_rate:int,
        sample_width:int,
        convert_sample_rete:bool=False,
        language:str = "ja-JP",
        key:str|None = None,
        timeout:float|None = None,
        challenge:int = 1,
        is_parallel_run:bool = False,
        parallel_max:int|None = None):

        super().__init__(sample_rate, sample_width, convert_sample_rete, language, key, timeout, challenge)
        self.__is_parallel_run = is_parallel_run
        self.__parallel = 3
        '''平行実行のスレッド数'''
        self.__parallel_successed = 0
        '''平行実行の成功回数'''
        self.__parallel_max = RecognitionModelGoogleDuplex.__MAX_PARALLEL
        '''平行実行の最大数'''
        if not parallel_max is None:
            self.__parallel_max = 0

    def _transcribe_impl(self, flac:google.EncodeData) -> TranscribeResult:
        def func(index:int = 0) -> TranscribeResult:
            if RecognitionModelGoogleDuplex.__MIN_PARALLEL < index:
                # 増加スレッドは遅延させてから実行する
                wait = math.ceil(index / RecognitionModelGoogleDuplex.__MIN_PARALLEL) - 1
                if(0 < wait):
                    time.sleep(wait * 0.1)
            r = google.recognize_google_duplex(
                flac,
                self._operation_timeout,
                self._key,
                self._language,
                0)
            return TranscribeResult(r.transcript, r.raw_data)

        if self.__is_parallel_run:
            thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=self.__parallel)
            try:
                e500 = 0
                futures = [thread_pool.submit(func, i) for i in range(self.__parallel)]
                ex:Exception | None = None
                for future in concurrent.futures.as_completed(futures):
                    try:
                        self.__parallel_successed += 1
                        if(RecognitionModelGoogleDuplex.__MAX_PARALLEL_SUCESS < self.__parallel_successed):
                            self.__parallel_successed = 0
                            self.__parallel = max(self.__parallel - 1, RecognitionModelGoogleDuplex.__MIN_PARALLEL)
                        return future.result()
                    except Exception as e:
                        if isinstance(e, google.HttpStatusError) and e.status_code == 500:
                            e500 += 1
                        if ex is None:
                            ex = e
                if e500 == self.__parallel:
                    self.__parallel_successed = 0
                    self.__parallel = min(self.__parallel + 1, self.__parallel_max)
                assert not ex is None
                raise ex
            finally:
                thread_pool.shutdown(wait=False)
        else:
            return func()


class TranscribeException(ex.IlluminateException):
    """
    認識に失敗した際なげる例外
    """
    pass
