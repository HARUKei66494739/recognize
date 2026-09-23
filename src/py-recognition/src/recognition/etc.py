# 雑多な認識クラスを置くところ

import numpy as np
from dataclasses import dataclass

import src.interface as inf
from src.lazy_loader import transformers, torch

from .common import RecognizeMicrophoneConfig


class ReazonSpeechMicrophoneConfig(RecognizeMicrophoneConfig):
    __DEFAULT_HEAD_DULATION = 0.3
    __DEFAULT_TAIL_DULATION = 0.

    def __init__(self, head_insert_duration:float | None = None, tail_insert_duration:float | None = None) -> None:
        super().__init__(
            head_insert_duration if not head_insert_duration is None else ReazonSpeechMicrophoneConfig.__DEFAULT_HEAD_DULATION,
            tail_insert_duration if not tail_insert_duration is None else ReazonSpeechMicrophoneConfig.__DEFAULT_TAIL_DULATION)



class RecognitionModelChrome(inf.RecognitionModel):
    def __init__(self):
        pass

    @property
    def required_sample_rate(self) -> int | None:
        return None

    def get_verbose(self, verbose:int) -> str | None:
        return None

    def get_log_info(self) -> str | None:
        return ""

    def transcribe(self, audio_data:np.ndarray) -> inf.TranscribeResult:
        return inf.TranscribeResult("", None)

@dataclass
class ReazonSpeechKSubword:
    """A subword with timestamp"""
    # Currently Subword only has a single-point timestamp.
    # Theoretically, we should be able to compute time ranges.
    seconds: float
    token: str


class RecognitionModelReazonSpeechK2(inf.RecognitionModel):
    SAMPLE_RATE = 16000

    def __init__(self) -> None:
        self.__model = RecognitionModelReazonSpeechK2._load_model()


    @property
    def required_sample_rate(self) -> int | None:
        return RecognitionModelReazonSpeechK2.SAMPLE_RATE

    def get_verbose(self, verbose:int) -> str | None:
        return None

    def get_log_info(self) -> str | None:
        return None

    def transcribe(self, audio_data:np.ndarray) -> inf.TranscribeResult:
        # TODO: 30秒警告の処理をいれる
        stream = self.__model.create_stream()
        stream.accept_waveform(
            RecognitionModelReazonSpeechK2.SAMPLE_RATE,
            (audio_data.astype(np.float32) / float(np.iinfo(np.int16).max)).tolist())
        self.__model.decode_stream(stream)

        subwords = []
        for t, s in zip(stream.result.tokens, stream.result.timestamps):
            subwords.append(ReazonSpeechKSubword(token=t, seconds=s))

        return inf.TranscribeResult(stream.result.text, subwords)


    # https://github.com/reazon-research/ReazonSpeech/blob/master/pkg/k2-asr/src/transcribe.py
    # The following definitions should match the repository layout
    # on Hugging Face Hub. Whenever the HF repo is changed, this
    # file should be updated accordingly.
    #
    # Multi lingual also has precision fp16, but is currently not
    # in use.
    #
    # https://huggingface.co/reazon-research/reazonspeech-k2-v2
    # https://huggingface.co/reazon-research/reazonspeech-k2-v2-ja-en
    # https://huggingface.co/reazon-research/reazonspeech-k2-v2-ja-en-mls-5k-corrected
    @staticmethod
    def _load_model(device="cpu", precision="fp32", language="ja"):
        import os
        import huggingface_hub
        import huggingface_hub.errors
        import sherpa_onnx
        """Load ReazonSpeech model from Hugging Face

        Args:
        device (str): "cpu", "cuda" or "coreml"
        precision (str): Whether to load quantized model ("fp32", "int8" or "int8-fp32")
        language (str): Whether to use japanese or bi-lingual model ("ja" or "ja-en" or "ja-en-mls-5k") 

        Returns:
        sherpa_onnx.OfflineRecognizer
        """

        if language == "ja":
            hf_repo_id = "reazon-research/reazonspeech-k2-v2"
            epochs = 99
        elif language == "ja-en":
            hf_repo_id = "reazon-research/reazonspeech-k2-v2-ja-en"
            epochs = 35
        elif language == "ja-en-mls-5k":
            hf_repo_id = "reazon-research/reazonspeech-k2-v2-ja-en-mls-5k-corrected"
            epochs = 21
        else:
            raise ValueError(f"Unknown language: '{language}'")

        hf_repo_files = {
            "fp32": {
                "tokens": "tokens.txt",
                "encoder": f"encoder-epoch-{epochs}-avg-1.onnx",
                "decoder": f"decoder-epoch-{epochs}-avg-1.onnx",
                "joiner": f"joiner-epoch-{epochs}-avg-1.onnx",
            },
            "int8": {
                "tokens": "tokens.txt",
                "encoder": f"encoder-epoch-{epochs}-avg-1.int8.onnx",
                "decoder": f"decoder-epoch-{epochs}-avg-1.int8.onnx",
                "joiner": f"joiner-epoch-{epochs}-avg-1.int8.onnx",
            },
            "int8-fp32": {
                "tokens": "tokens.txt",
                "encoder": f"encoder-epoch-{epochs}-avg-1.int8.onnx",
                "decoder": f"decoder-epoch-{epochs}-avg-1.onnx",
                "joiner": f"joiner-epoch-{epochs}-avg-1.int8.onnx",
            }
        }

        if precision not in hf_repo_files:
            raise ValueError("Unknown precision: '%s'" % precision)

        files = hf_repo_files[precision]

        # If the model is found in the local cache, do not connect
        # to Hugging Face.
        try:
            basedir = huggingface_hub.snapshot_download(hf_repo_id, local_files_only=True)
        except huggingface_hub.errors.LocalEntryNotFoundError:
            basedir = huggingface_hub.snapshot_download(hf_repo_id)

        return sherpa_onnx.OfflineRecognizer.from_transducer(
            tokens=os.path.join(basedir, files["tokens"]),
            encoder=os.path.join(basedir, files['encoder']),
            decoder=os.path.join(basedir, files['decoder']),
            joiner=os.path.join(basedir, files['joiner']),
            num_threads=1,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
            provider=device,
        )


class RecognitionModelKodamaStreaming(inf.RecognitionModel):
    SAMPLE_RATE = 16000
    MODEL_ID = "ayousanz/kodama-ja-streaming-small"

    def __init__(self) -> None:
        #self.__device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.__device = "cpu"

        self.__model = transformers.MoonshineStreamingForConditionalGeneration \
            .from_pretrained(RecognitionModelKodamaStreaming.MODEL_ID) \
            .to(self.__device)
        self.__processor = transformers.AutoProcessor \
            .from_pretrained(RecognitionModelKodamaStreaming.MODEL_ID)


    @property
    def required_sample_rate(self) -> int | None:
        return RecognitionModelKodamaStreaming.SAMPLE_RATE

    def get_verbose(self, verbose:int) -> str | None:
        return None

    def get_log_info(self) -> str | None:
        return None

    def transcribe(self, audio_data:np.ndarray) -> inf.TranscribeResult:
        inputs = self.__processor(
            ((audio_data.astype(np.float32) / float(np.iinfo(np.int16).max)).tolist()),
            return_tensors="pt",
            sampling_rate=RecognitionModelKodamaStreaming.SAMPLE_RATE).to(self.__device)

        token_limit_factor = 6.5 / self.__processor.feature_extractor.sampling_rate
        max_length = int((inputs.attention_mask.sum(dim=-1) * token_limit_factor).max().item())

        ids = self.__model.generate(**inputs, max_length=max_length)
        ret = self.__processor.decode(ids[0], skip_special_tokens=True)
        return inf.TranscribeResult(ret, ret)
