import os
import time
import math
import numpy as np
import speech_recognition as sr
import urllib.error as urlerr
import requests.exceptions
import concurrent.futures
from typing import Any, NamedTuple, Callable, Iterator

import src.interface as inf
import src.exception as ex
import src.google_recognizers as google
import src.val

from .common import RecognizeMicrophoneConfig, TranscribeException

class GoogleTranscribeExtend(NamedTuple):
    """
    RecognitionModel#transcribeの戻り値データ型
    """
    raw_data:Any
    retry_history:list[Exception]

    def __str__(self) -> str:
        if 0 < len(self.retry_history):
            clazz = os.linesep.join([f"{type(i)}:{i}"for i in self.retry_history])
            return f"{self.raw_data}{os.linesep}retry-stack{os.linesep}{clazz}"
        else:
            return str(self.raw_data)

class GoogleMicrophoneConfig(RecognizeMicrophoneConfig):
    __DEFAULT_HEAD_DULATION = 0.2
    __DEFAULT_TAIL_DULATION = 0.25

    def __init__(self, head_insert_duration:float | None = None, tail_insert_duration:float | None = None) -> None:
        super().__init__(
            head_insert_duration if not head_insert_duration is None else GoogleMicrophoneConfig.__DEFAULT_HEAD_DULATION,
            tail_insert_duration if not tail_insert_duration is None else GoogleMicrophoneConfig.__DEFAULT_TAIL_DULATION)


class RecognitionModelGoogleApi(inf.RecognitionModel):
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

    def get_verbose(self, verbose:int) -> str | None:
        return None

    def get_log_info(self) -> str | None:
        return ""

    def transcribe(self, audio_data:np.ndarray) -> inf.TranscribeResult:
        flac = google.encode_falc(
            sr.AudioData(audio_data.astype(np.int16, order="C"), self.__sample_rate, self.__sample_width),
            None if not self.__convert_sample_rete else 16000)

        his = []
        loop = 0
        while loop < self.__max_loop:
            try:
                r = self._transcribe_impl(flac)
                return inf.TranscribeResult(r.transcribe, GoogleTranscribeExtend(r.extend_data, his))
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
            except ParallelTranscribeException as e:
                if (e.is_error500) and (1 < self.__max_loop):
                    his.append(e)
                else:
                    raise TranscribeException("google音声認識でHTTPエラー: {}".format(e), e)
            loop += 1
        clazz = ",".join([f"{type(i)}"for i in his])
        raise TranscribeException(f"{self.__max_loop}回試行しましたが失敗しました({clazz}])")
 
    def _transcribe_impl(self, flac:google.EncodeData) -> inf.TranscribeResult:
        ...

class RecognitionModelGoogle(RecognitionModelGoogleApi):
    """
    認識モデルのgoogle音声認識API v2実装
    """
    def __init__(
        self,
        sample_rate: int,
        sample_width: int,
        convert_sample_rete: bool=False,
        language: str = "ja-JP",
        profanity_filter:bool = False,        
        key: str | None = None,
        timeout: float | None = None,
        challenge: int = 1):
        super().__init__(sample_rate, sample_width, convert_sample_rete, language, key, timeout, challenge)
        if profanity_filter:
            self.__profanity_filter = 2
        else:
            self.__profanity_filter = 0

    def _transcribe_impl(self, flac:google.EncodeData) -> inf.TranscribeResult:
        r = google.recognize_google(
            flac,
            self._operation_timeout,
            self._key,
            self._language,
            self.__profanity_filter)
        return inf.TranscribeResult(r.transcript, r.raw_data)


class RecognitionModelGoogleDuplex(RecognitionModelGoogleApi):
    """
    認識モデルのgoogle全二重API実装
    """

    __MAX_PARALLEL_SUCESS = 3
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
        profanity_filter:bool = False,
        key:str|None = None,
        timeout:float|None = None,
        challenge:int = 1,
        is_parallel_run:bool = False,
        parallel_max:int|None = None,
        parallel_reduce_count:int|None = None):

        super().__init__(sample_rate, sample_width, convert_sample_rete, language, key, timeout, challenge)
        if profanity_filter:
            self.__profanity_filter = 2
        else:
            self.__profanity_filter = 0
        self.__is_parallel_run = is_parallel_run
        self.__parallel = 3
        '''平行実行のスレッド数'''
        self.__parallel_successed = 0
        '''平行実行の成功回数'''
        self.__parallel_max = RecognitionModelGoogleDuplex.__MAX_PARALLEL
        '''平行実行の最大数'''
        if not parallel_max is None:
            self.__parallel_max = max(parallel_max, RecognitionModelGoogleDuplex.__MIN_PARALLEL)
        self.__parallel_reduce_count = RecognitionModelGoogleDuplex.__MAX_PARALLEL_SUCESS
        '''平行実行を減少させるための必要な成功数'''
        if not parallel_reduce_count is None:
            self.__parallel_reduce_count = max(parallel_reduce_count, 1)

    def get_verbose(self, verbose:int) -> str | None:
        if verbose < 2:
            return None
        if not self.__is_parallel_run:
            return None
        return f"current parallel num = {self.__parallel}"

    def get_log_info(self) -> str | None:
        return f"current parallel num = {self.__parallel}"

    def _transcribe_impl(self, flac:google.EncodeData) -> inf.TranscribeResult:
        class Extend(NamedTuple):
            exceptions:list[Exception]
            raw_data:str

            def __str__(self) -> str:
                if 0 < len(self.exceptions):
                    return f"{self.raw_data}{os.linesep}{len(self.exceptions)}回の失敗:{os.linesep}{f'{os.linesep}'.join(map(lambda x: f'{type(x)}:{x}', self.exceptions))}"
                else:
                    return f"{self.raw_data}"
        def func(index:int = 0, delay_ratio=0.1) -> inf.TranscribeResult:
            if RecognitionModelGoogleDuplex.__MIN_PARALLEL < index:
                # 増加スレッドは遅延させてから実行する
                wait = math.ceil(index / RecognitionModelGoogleDuplex.__MIN_PARALLEL) - 1
                if(0 < wait):
                    time.sleep(wait * delay_ratio)
            r = google.recognize_google_duplex(
                flac,
                self._operation_timeout,
                self._key,
                self._language,
                self.__profanity_filter)
            return inf.TranscribeResult(r.transcript, r.raw_data)

        if self.__is_parallel_run:
            thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=self.__parallel)
            try:
                futures = [thread_pool.submit(func, i) for i in range(self.__parallel)]
                ex:list[Exception] = []
                for future in concurrent.futures.as_completed(futures):
                    try:
                        r = future.result()
                        self.__parallel_successed += 1
                        if(self.__parallel_reduce_count < self.__parallel_successed):
                            self.__parallel_successed = 0
                            self.__parallel = max(self.__parallel - 1, RecognitionModelGoogleDuplex.__MIN_PARALLEL)
                        return inf.TranscribeResult(r.transcribe, Extend(ex, f"{r.extend_data}"))
                    except Exception as e:
                        ex.append(e)

                raise_ex = ParallelTranscribeException("すべての並列実行が失敗", ex)
                if raise_ex.is_error500:
                    self.__parallel_successed = 0
                    self.__parallel = min(self.__parallel + 1, self.__parallel_max)
                raise raise_ex
            finally:
                thread_pool.shutdown(wait=False)
        else:
            return func()

class RecognitionModelGoogleMix(RecognitionModelGoogleApi):
    """
    認識モデルのgoogle全二重API実装
    """

    __MAX_PARALLEL_SUCESS = 3
    '''スレッド数を下げるために必要な平行実行の成功回数(duplex)'''
    __MIN_PARALLEL_DUPLEX = 3
    '''変動スレッド数の最低値(duplex)'''
    __MAX_PARALLEL_DUPLEX = 6
    '''変動スレッド数の最大値(duplex)'''

    API_RECOGNIZE = 1
    '''API-No:recognize API'''
    API_DUPLEX = 2
    '''API-No:duplex API'''


    def __init__(
        self,
        sample_rate:int,
        sample_width:int,
        convert_sample_rete:bool=False,
        language:str = "ja-JP",
        profanity_filter:bool = False,
        key:str|None = None,
        timeout:float|None = None,
        challenge:int = 1,
        parallel_max_duplex:int|None = None,
        parallel_reduce_count_duplex:int|None = None):

        super().__init__(sample_rate, sample_width, convert_sample_rete, language, key, timeout, challenge)
        if profanity_filter:
            self.__profanity_filter = 2
        else:
            self.__profanity_filter = 0        
        self.__parallel_recognize = 1
        '''平行実行のスレッド数(recognize)'''

        self.__parallel__duplex = 3
        '''平行実行のスレッド数(duplex)'''
        self.__parallel_successed__duplex = 0
        '''平行実行の成功回数(duplex)'''
        self.__parallel_max__duplex = RecognitionModelGoogleMix.__MAX_PARALLEL_DUPLEX
        '''平行実行の最大数(duplex)'''
        if not parallel_max_duplex is None:
            self.__parallel_max__duplex = max(parallel_max_duplex, RecognitionModelGoogleMix.__MIN_PARALLEL_DUPLEX)
        self.__parallel_reduce_count__duplex = RecognitionModelGoogleMix.__MAX_PARALLEL_SUCESS
        '''平行実行を減少させるための必要な成功数(duplex)'''
        if not parallel_reduce_count_duplex is None:
            self.__parallel_reduce_count__duplex = max(parallel_reduce_count_duplex, 1)

    def get_verbose(self, verbose:int) -> str | None:
        if verbose < 2:
            return None
        return f"current parallel num = ({ self.__parallel_recognize}, {self.__parallel__duplex})"

    def get_log_info(self) -> str | None:
        return f"current parallel num = ({ self.__parallel_recognize}, {self.__parallel__duplex})"

    def _transcribe_impl(self, flac:google.EncodeData) -> inf.TranscribeResult:
        class FutureResult(NamedTuple):
            api_no:int
            result:inf.TranscribeResult

        class Extend(NamedTuple):
            exceptions:list[Exception]
            api_no:int
            raw_data:str

            def __str__(self) -> str:
                def api(i:int):
                    if i == RecognitionModelGoogleMix.API_RECOGNIZE:
                        return "recognize-api"
                    if i == RecognitionModelGoogleMix.API_DUPLEX:
                        return "duplex-api"
                    return "unknown-api"
                if 0 < len(self.exceptions):
                    return f"transcribe:{api(self.api_no)}{os.linesep}{self.raw_data}{os.linesep}{len(self.exceptions)}回の失敗:{os.linesep}{f'{os.linesep}'.join(map(lambda x: f'{type(x)}:{x}', self.exceptions))}"
                else:
                    return f"transcribe:{api(self.api_no)}{os.linesep}{self.raw_data}"

        def func_recognize(_:int = 0, __=0.1) -> FutureResult:
            r = google.recognize_google(
                flac,
                self._operation_timeout,
                self._key,
                self._language,
                self.__profanity_filter)
            return FutureResult(RecognitionModelGoogleMix.API_RECOGNIZE, inf.TranscribeResult(r.transcript, r.raw_data))

        def func_duplex(index:int = 0, delay_ratio=0.1) -> FutureResult:
            if RecognitionModelGoogleMix.__MIN_PARALLEL_DUPLEX < index:
                # 増加スレッドは遅延させてから実行する
                wait = math.ceil(index / RecognitionModelGoogleMix.__MIN_PARALLEL_DUPLEX) - 1
                if(0 < wait):
                    time.sleep(wait * delay_ratio)
            r = google.recognize_google_duplex(
                flac,
                self._operation_timeout,
                self._key,
                self._language,
                self.__profanity_filter)
            return FutureResult(RecognitionModelGoogleMix.API_DUPLEX, inf.TranscribeResult(r.transcript, r.raw_data))


        thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=self.__parallel__duplex + 2)
        try:
            futures = [thread_pool.submit(func_recognize) for _ in range( self.__parallel_recognize)] \
                + [thread_pool.submit(func_duplex, i) for i in range(self.__parallel__duplex)]
            ex:list[Exception] = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    r = future.result()
                    if r.api_no == RecognitionModelGoogleMix.API_DUPLEX:
                        self.__parallel_successed__duplex += 1
                        if(self.__parallel_reduce_count__duplex < self.__parallel_successed__duplex):
                            self.__parallel_successed__duplex = 0
                            self.__parallel__duplex = max(self.__parallel__duplex - 1, RecognitionModelGoogleMix.__MIN_PARALLEL_DUPLEX)
                    return inf.TranscribeResult(r.result.transcribe, Extend(ex, r.api_no, f"{r.result.extend_data}"))
                except Exception as e:
                    ex.append(e)

            raise_ex = ParallelTranscribeException("すべての並列実行が失敗", ex)
            if raise_ex.is_error500:
                self.__parallel_successed__duplex = 0
                self.__parallel = min(self.__parallel + 1, self.__parallel_max__duplex)
            raise raise_ex
        finally:
            thread_pool.shutdown(wait=False)


class ParallelTranscribeException(ex.IlluminateException):
    def __init__(self, message: str, exceptions:list[Exception]):
        super().__init__(message, None)
        self.__exceptions = exceptions

        self.__is_error500 = not (False in map(
            lambda x:isinstance(x, google.HttpStatusErrorDuplex)
              and x.status_code == 500,
            exceptions))

    def __str__(self) -> str:
        return f"並列実行がすべて失敗しました parallel={len(self.__exceptions)}, 500error={self.is_error500}, exception={','.join(list(map(lambda x: f'{type(x)}', self.__exceptions)))}"

    @property
    def is_error500(self) -> bool:
        return self.__is_error500