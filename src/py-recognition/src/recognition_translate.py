import numpy as np
from typing import Any, NamedTuple, Callable, List, Dict

import src.exception as ex
import src.recognition as recognition


class TranslateResult(NamedTuple):
    """
    RecognitionModel#transcribeの戻り値データ型
    """
    translate:str
    extend_data:Any


class TranslateModel:
    """
    認識モデル抽象基底クラス
    """

    @property
    def required_sample_rate(self) -> int | None:
        ...

    def translate(self, audio_data:np.ndarray, text:str) -> TranslateResult:
        ...

#class TranslateException(ex.IlluminateException):
#    """
#    認識に失敗した際なげる例外
#    """
#    pass
