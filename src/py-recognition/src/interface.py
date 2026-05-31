import numpy
from typing import Any, NamedTuple, Callable, List, Dict

#
# VAD
#


class VoiceActivityDetectorFilter:
    @property
    def mic_pause_duration(self) -> float:
        ...

    def check(self, data:bytes) -> bool:
        ...

#
# NoiseFilter
#

class NoiseFilter:
    """
    ノイズフィルタ抽象基底クラス
    """
    def __init__(self, sampling_rate:int) -> None:
        self.sampling_rate = sampling_rate

    def filter(self, data:numpy.ndarray): # np.ndarray[np.complex128]
        """
        ノイズフィルターをdataに対して行います。dataの内容は変更されます。
        """
        ...

#
# recoginze
#

class TranscribeResult(NamedTuple):
    """
    RecognitionModel#transcribeの戻り値データ型
    """
    transcribe:str
    extend_data:Any

class TranslateResult(NamedTuple):
    """
    RecognitionModel#transcribeの戻り値データ型
    """
    translate:str
    extend_data:Any


class RecognitionModel:
    """
    認識モデル抽象基底クラス
    """

    @property
    def required_sample_rate(self) -> int | None:
        ...

    def transcribe(self, audio_data:numpy.ndarray) -> TranscribeResult:
        ...

    def get_verbose(self, verbose:int) -> str | None:
        ...

    def get_log_info(self) -> str | None:
        ...


class TranslateModel:
    """
    認識モデル抽象基底クラス
    """

    @property
    def required_sample_rate(self) -> int | None:
        ...

    def translate(self, audio_data:numpy.ndarray, text:str) -> TranslateResult:
        ...