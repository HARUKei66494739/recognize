import numpy as np

import src.interface as inf

from src.lazy_loader import moonshine_voice


class RecognitionModelMoonShine(inf.RecognitionModel):
    SAMPLE_RATE = 16000

    def __init__(self) -> None:
        model_path, model_arch = moonshine_voice.get_model_for_language("ja")
        self.__transcriber = moonshine_voice.Transcriber(
            model_path=model_path,
            model_arch=model_arch)

    @property
    def required_sample_rate(self) -> int | None:
        return RecognitionModelMoonShine.SAMPLE_RATE

    def get_verbose(self, verbose:int) -> str | None:
        return None

    def get_log_info(self) -> str | None:
        return None

    def transcribe(self, audio_data:np.ndarray) -> inf.TranscribeResult:
        ret = self.__transcriber.transcribe_without_streaming(
            (audio_data.astype(np.float32) / float(np.iinfo(np.int16).max)).tolist())
        return inf.TranscribeResult("".join(f"{line.text}" for line in ret.lines), ret)
