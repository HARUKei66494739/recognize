import numpy as np
from typing import Any, NamedTuple, Callable, Iterator

import src.interface as inf
import src.exception as ex
import src.val

from src.lazy_loader import whisper, faster_whisper, transformers, torch, moonshine_voice

from .common import TranscribeException

class RecognitionModelWhisper(inf.RecognitionModel):
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

    def get_verbose(self, verbose:int) -> str | None:
        return None

    def transcribe(self, audio_data:np.ndarray) -> inf.TranscribeResult:
        r = self.audio_model.transcribe(
            torch.from_numpy(audio_data.astype(np.float32) / float(np.iinfo(np.int16).max)),
            language = self.__language,
            fp16 = self.__is_fp16)["text"]
        if isinstance(r, str):
            return inf.TranscribeResult(r, None)
        if isinstance(r, list):
            return inf.TranscribeResult("".join(r), None)
        raise ex.ProgramError(f"Whisper.transcribeから意図しない戻り値型:{type(r)}")

    def get_log_info(self) -> str:
        return ""


class RecognitionModelWhisperFaster(inf.RecognitionModel):
    """
    認識モデルのfaster_whisper実装
    """
    def __init__(
        self,
        model:str,
        language:str,
        device:str,
        device_index:int,
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
        self.audio_model = faster_whisper.WhisperModel(
            m,
            run_device,
            device_index = device_index,
            compute_type = compute_type,
            download_root = download_root)

    @property
    def required_sample_rate(self) -> int | None:
        return 16000

    def get_verbose(self, verbose:int) -> str | None:
        return None

    def get_log_info(self) -> str:
        return ""

    def transcribe(self, audio_data:np.ndarray) -> inf.TranscribeResult:
        segments, _  = self.audio_model.transcribe(
            audio_data.astype(np.float32) / float(np.iinfo(np.int16).max),
            language = self.__language,
            beam_size=5)
            #max_new_tokens = 128,
            #condition_on_previous_text = False)
        c = []
        for s in segments:
            c.append(s.text)
        return inf.TranscribeResult("".join(c), segments)


class RecognizeAndTranslateModelKotobaWhisper(inf.RecognitionModel, inf.TranslateModel):
    def __init__(self, device:str, device_index:int) -> None:
        torch_dtype = torch.bfloat16 if device == "cuda" else torch.float32
        model_kwargs:Any = {"attn_implementation": "sdpa"} if torch.cuda.is_available() else {}
        model_kwargs["torch_dtype"] = torch_dtype

        if device == "cuda":
            device = f"{device}:{device_index}"
        self.__pipe = transformers.pipeline(
            "automatic-speech-recognition",
            model="kotoba-tech/kotoba-whisper-bilingual-v1.0",
            device=device,
            model_kwargs=model_kwargs,
            chunk_length_s=15,
            batch_size=16
        )
        self.__generate_kwargs_translate = {"language": "en", "task": "translate"}
        self.__generate_kwargs_ttranscribe = {"language": "ja", "task": "transcribe"}

    @property
    def required_sample_rate(self) -> int | None:
        return 16000

    def translate(self, audio_data:np.ndarray, text:str) -> inf.TranslateResult:
        reslut = self.__pipe(
            audio_data.astype(np.float16) / float(np.iinfo(np.int16).max),
            generate_kwargs = self.__generate_kwargs_translate)
        r:str = reslut["text"] #type: ignore
        return inf.TranslateResult(r, reslut)

    def get_verbose(self, verbose:int) -> str | None:
        return None

    def transcribe(self, audio_data:np.ndarray) -> inf.TranscribeResult:
        audio = audio_data.astype(np.float16) / float(np.iinfo(np.int16).max)
        sample_rate = self.required_sample_rate
        assert(sample_rate is not None)

        reslut = self.__pipe(
            audio,
            return_timestamps=True,
            generate_kwargs = self.__generate_kwargs_ttranscribe)
        print(reslut["chunks"])
        if "chunks" in reslut and len(reslut["chunks"]) == 1 and "timestamp" in reslut["chunks"][0]: #type: ignore
            ts = reslut["chunks"][0]["timestamp"] #type: ignore
            if ts[0] == 0.0 and ts[1] == 0.1:
                raise TranscribeException(f"ノイズ判定:{reslut}") 
        r = reslut["text"] #type: ignore
        if isinstance(r, str):
            return inf.TranscribeResult(r, reslut)
        if isinstance(r, list):
            return inf.TranscribeResult("".join(r), reslut)
        raise ex.ProgramError(f"pipelineから意図しない戻り値型:{type(r)}")


class TranslateModelTranslateGemma(inf.TranslateModel):
    def __init__(self, device:str, device_index:int, parameter_size:str, target:str) -> None:
        torch_dtype = torch.bfloat16 if device == "cuda" else torch.float32

        if device == "cuda":
            device = f"{device}:{device_index}"
        self.__pipe = transformers.pipeline(
            "image-text-to-text",
            model=f"google/translategemma-{parameter_size}b-it",
            device=device,
            dtype=torch_dtype
        )
        self.__source_lang_code = "ja-JP"
        self.__target_lang_code = target

    @property
    def required_sample_rate(self) -> int | None:
        return None

    def translate(self, audio_data:np.ndarray, text:str) -> inf.TranslateResult:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "source_lang_code": self.__source_lang_code,
                        "target_lang_code": self.__target_lang_code,
                        "text": text,
                    }
                ],
            }
        ]
        output = self.__pipe(text=messages, max_new_tokens=200) #type: ignore
        r:str = output[0]["generated_text"][-1]["content"] #type: ignore
        return inf.TranslateResult(r, output)
