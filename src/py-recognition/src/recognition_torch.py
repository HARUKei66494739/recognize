import os
import time
import math
import numpy as np
import speech_recognition as sr
import urllib.error as urlerr
from typing import Any, NamedTuple, Callable

import src.exception as ex
from src.recognition import RecognitionModel, TranscribeResult, TranscribeException
from src.recognition_translate import TranslateModel, TranslateResult


try:
    import whisper # type: ignore
    import torch # type: ignore
except:
    pass
else:
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

        def get_verbose(self, verbose:int) -> str | None:
            return None

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

        def get_log_info(self) -> str:
            return ""

try:
    import faster_whisper # type: ignore
    import torch # type: ignore
except:
    pass
else:
    class RecognitionModelWhisperFaster(RecognitionModel):
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

        def transcribe(self, audio_data:np.ndarray) -> TranscribeResult:
            segments, _  = self.audio_model.transcribe(
                audio_data.astype(np.float32) / float(np.iinfo(np.int16).max),
                language = self.__language,
                beam_size=5)
                #max_new_tokens = 128,
                #condition_on_previous_text = False)
            c = []
            for s in segments:
                c.append(s.text)
            return TranscribeResult("".join(c), segments)


try:
    from transformers import pipeline  # type: ignore
    import stable_whisper # type: ignore
    import torch # type: ignore
    import stable_whisper
    from typing import Optional
except:
    pass
else:
    # kotoba_whisper 2.1から移植をベースに変更
    from typing import Union, Optional, Dict, List, Any
    import requests

    import torch
    import numpy as np

    from transformers.pipelines.audio_utils import ffmpeg_read
    from transformers.pipelines.automatic_speech_recognition import AutomaticSpeechRecognitionPipeline, chunk_iter
    from transformers.utils import is_torchaudio_available
    from transformers.modeling_utils import PreTrainedModel
    from transformers.tokenization_utils import PreTrainedTokenizer
    from transformers.feature_extraction_sequence_utils import SequenceFeatureExtractor
    from stable_whisper import WhisperResult

    from transformers.utils import logging
    logging.set_verbosity_error() 

    def _fix_timestamp(sample_rate: int, result: List[Dict[str, Any]], audio: np.ndarray) -> WhisperResult:

        def replace_none_ts(parts):
            total_dur = round(audio.shape[-1] / sample_rate, 3)
            _medium_dur:Any = None
            _ts_nonzero_mask = None

            def ts_nonzero_mask() -> np.ndarray:
                nonlocal _ts_nonzero_mask
                if _ts_nonzero_mask is None:
                    _ts_nonzero_mask = np.array([(p['end'] or p['start']) is not None for p in parts])
                return _ts_nonzero_mask

            def medium_dur() -> float:
                nonlocal _medium_dur
                if _medium_dur is None:
                    nonzero_dus = [p['end'] - p['start'] for p in parts if None not in (p['end'], p['start'])]
                    nonzero_durs = np.array(nonzero_dus)
                    _medium_dur = np.median(nonzero_durs) * 2 if len(nonzero_durs) else 2.0
                return _medium_dur

            def _curr_max_end(start: float, next_idx: float) -> float:
                max_end = total_dur
                if next_idx != len(parts):
                    mask = np.flatnonzero(ts_nonzero_mask()[next_idx:])
                    if len(mask):
                        _part = parts[mask[0]+next_idx]
                        max_end = _part['start'] or _part['end']

                new_end = round(start + medium_dur(), 3)
                if new_end > max_end:
                    return max_end
                return new_end

            for i, part in enumerate(parts, 1):
                if part['start'] is None:
                    is_first = i == 1
                    if is_first:
                        new_start = round((part['end'] or 0) - medium_dur(), 3)
                        part['start'] = max(new_start, 0.0)
                    else:
                        part['start'] = parts[i - 2]['end']
                if part['end'] is None:
                    no_next_start = i == len(parts) or parts[i]['start'] is None
                    part['end'] = _curr_max_end(part['start'], i) if no_next_start else parts[i]['start']

        words = [dict(start=word['timestamp'][0], end=word['timestamp'][1], word=word['text']) for word in result]
        replace_none_ts(words)
        return WhisperResult([words], force_order=True, check_sorted=True)


    def fix_timestamp(pipeline_output: List[Dict[str, Any]], audio: np.ndarray, sample_rate: int) -> List[Dict[str, Any]]:
        result = _fix_timestamp(sample_rate=sample_rate, audio=audio, result=pipeline_output)
        result.adjust_by_silence(
            audio,
            #vad=True,
            q_levels=20,
            k_size=5,
            sample_rate=sample_rate,
            min_word_dur=None,
            word_level=True,
            verbose=None, # stable-tsの実装なんか実装おかしくない
            nonspeech_error=0.1,
            use_word_position=True
        )
        if result.has_words:
            result.regroup(True)
        return [{"timestamp": [s.start, s.end], "text": s.text} for s in result.segments]


    class KotobaWhisperPipeline(AutomaticSpeechRecognitionPipeline):

        def __init__(self,
                    model: PreTrainedModel,
                    feature_extractor: Optional[Union[SequenceFeatureExtractor, str]] = None,
                    tokenizer: Optional[PreTrainedTokenizer] = None,
                    device: Optional[Union[int, torch.device]] = None,
                    torch_dtype: Optional[Union[str, torch.dtype]] = None,
                    punctuator: bool = True,
                    stable_ts: bool = False,
                    **kwargs):
            self.type = "seq2seq_whisper"
            self.stable_ts = stable_ts
            super().__init__(
                model=model,
                feature_extractor=feature_extractor, #type: ignore
                tokenizer=tokenizer,
                device=device, #type: ignore
                torch_dtype=torch_dtype,
                **kwargs
            )

        def preprocess(self, inputs, chunk_length_s=0, stride_length_s=None):
            if isinstance(inputs, str):
                if inputs.startswith("http://") or inputs.startswith("https://"):
                    # We need to actually check for a real protocol, otherwise it's impossible to use a local file
                    # like http_huggingface_co.png
                    inputs = requests.get(inputs).content
                else:
                    with open(inputs, "rb") as f:
                        inputs = f.read()

            if isinstance(inputs, bytes):
                inputs = ffmpeg_read(inputs, self.feature_extractor.sampling_rate) #type:ignore

            stride = None
            extra = {}
            if isinstance(inputs, dict):
                stride = inputs.pop("stride", None)
                # Accepting `"array"` which is the key defined in `datasets` for
                # better integration
                if not ("sampling_rate" in inputs and ("raw" in inputs or "array" in inputs)):
                    raise ValueError(
                        "When passing a dictionary to AutomaticSpeechRecognitionPipeline, the dict needs to contain a "
                        '"raw" key containing the numpy array representing the audio and a "sampling_rate" key, '
                        "containing the sampling_rate associated with that array"
                    )

                _inputs = inputs.pop("raw", None)
                if _inputs is None:
                    # Remove path which will not be used from `datasets`.
                    inputs.pop("path", None)
                    _inputs = inputs.pop("array", None)
                in_sampling_rate = inputs.pop("sampling_rate")
                extra = inputs
                inputs = _inputs
                if in_sampling_rate != self.feature_extractor.sampling_rate: #type:ignore
                    if is_torchaudio_available():
                        from torchaudio import functional as F
                    else:
                        raise ImportError(
                            "torchaudio is required to resample audio samples in AutomaticSpeechRecognitionPipeline. "
                            "The torchaudio package can be installed through: `pip install torchaudio`."
                        )

                    inputs = F.resample(
                        torch.from_numpy(inputs), in_sampling_rate, self.feature_extractor.sampling_rate #type:ignore
                    ).numpy()
                    ratio = self.feature_extractor.sampling_rate / in_sampling_rate #type:ignore
                else:
                    ratio = 1
                if stride is not None:
                    if stride[0] + stride[1] > inputs.shape[0]:
                        raise ValueError("Stride is too large for input")

                    # Stride needs to get the chunk length here, it's going to get
                    # swallowed by the `feature_extractor` later, and then batching
                    # can add extra data in the inputs, so we need to keep track
                    # of the original length in the stride so we can cut properly.
                    stride = (inputs.shape[0], int(round(stride[0] * ratio)), int(round(stride[1] * ratio)))
            if not isinstance(inputs, np.ndarray):
                raise ValueError(f"We expect a numpy ndarray as input, got `{type(inputs)}`")
            if len(inputs.shape) != 1:
                raise ValueError("We expect a single channel audio input for AutomaticSpeechRecognitionPipeline")

            if chunk_length_s:
                if stride_length_s is None:
                    stride_length_s = chunk_length_s / 6

                if isinstance(stride_length_s, (int, float)):
                    stride_length_s = [stride_length_s, stride_length_s]

                # XXX: Carefuly, this variable will not exist in `seq2seq` setting.
                # Currently chunking is not possible at this level for `seq2seq` so
                # it's ok.
                align_to = getattr(self.model.config, "inputs_to_logits_ratio", 1)
                chunk_len = int(round(chunk_length_s * self.feature_extractor.sampling_rate / align_to) * align_to)        #type:ignore
                stride_left = int(round(stride_length_s[0] * self.feature_extractor.sampling_rate / align_to) * align_to)  #type:ignore
                stride_right = int(round(stride_length_s[1] * self.feature_extractor.sampling_rate / align_to) * align_to) #type:ignore

                if chunk_len < stride_left + stride_right:
                    raise ValueError("Chunk length must be superior to stride length")

                for item in chunk_iter(
                        inputs, self.feature_extractor, chunk_len, stride_left, stride_right, self.torch_dtype
                ):
                    item["audio_array"] = inputs
                    yield item
            else:
                if inputs.shape[0] > self.feature_extractor.n_samples: #type:ignore
                    processed = self.feature_extractor( #type:ignore
                        inputs,
                        sampling_rate=self.feature_extractor.sampling_rate, #type:ignore
                        truncation=False,
                        padding="longest",
                        return_tensors="pt",
                    )
                else:
                    processed = self.feature_extractor( #type:ignore
                        inputs, sampling_rate=self.feature_extractor.sampling_rate, return_tensors="pt" #type:ignore
                    )

                if self.torch_dtype is not None:
                    processed = processed.to(dtype=self.torch_dtype)
                if stride is not None:
                    processed["stride"] = stride
                yield {"is_last": True, "audio_array": inputs, **processed, **extra}

        def _forward(self, model_inputs, return_timestamps=False, **generate_kwargs):
            attention_mask = model_inputs.pop("attention_mask", None)
            stride = model_inputs.pop("stride", None)
            is_last = model_inputs.pop("is_last")
            audio_array = model_inputs.pop("audio_array")
            encoder = self.model.get_encoder()
            # Consume values so we can let extra information flow freely through
            # the pipeline (important for `partial` in microphone)
            if type(return_timestamps) is not bool:
                raise ValueError("return_timestamps should be bool")
            if "input_features" in model_inputs:
                inputs = model_inputs.pop("input_features")
            elif "input_values" in model_inputs:
                inputs = model_inputs.pop("input_values")
            else:
                raise ValueError(
                    "Seq2Seq speech recognition model requires either a "
                    f"`input_features` or `input_values` key, but only has {model_inputs.keys()}"
                )

            # custom processing for Whisper timestamps and word-level timestamps
            generate_kwargs["return_timestamps"] = True
            if inputs.shape[-1] > self.feature_extractor.nb_max_frames: #type:ignore
                generate_kwargs["input_features"] = inputs
            else:
                generate_kwargs["encoder_outputs"] = encoder(inputs, attention_mask=attention_mask)

            tokens = self.model.generate(attention_mask=attention_mask, **generate_kwargs)
            # whisper longform generation stores timestamps in "segments"
            out = {"tokens": tokens}
            if self.type == "seq2seq_whisper":
                if stride is not None:
                    out["stride"] = stride

            # Leftover
            extra = model_inputs
            return {"is_last": is_last, "audio_array": audio_array, **out, **extra}

        def postprocess(self,
                        model_outputs,
                        decoder_kwargs: Optional[Dict] = None,
                        return_timestamps=None,
                        return_language=None):
            assert len(model_outputs) > 0
            for model_output in model_outputs:
                audio_array = model_output.pop("audio_array")[0]
            outputs = super().postprocess(
                model_outputs=model_outputs,
                decoder_kwargs=decoder_kwargs,
                return_timestamps=True,
                return_language=return_language
            )
            if self.stable_ts:
                outputs["chunks"] = fix_timestamp(
                    pipeline_output=outputs["chunks"], audio=audio_array, sample_rate=self.feature_extractor.sampling_rate #type:ignore
                )
            outputs["text"] = "".join([c["text"] for c in outputs["chunks"]])
            if not return_timestamps:
                outputs.pop("chunks")
            return outputs


    class RecognizeAndTranslateModelKotobaWhisper(RecognitionModel, TranslateModel):
        def __init__(self, device:str, device_index:int) -> None:
            torch_dtype = torch.bfloat16 if device == "cuda" else torch.float32
            model_kwargs:Any = {"attn_implementation": "sdpa"} if torch.cuda.is_available() else {}
            model_kwargs["torch_dtype"] = torch_dtype

            if device == "cuda":
                device = f"{device}:{device_index}"
            self.__pipe = pipeline(
                "automatic-speech-recognition",
                model="kotoba-tech/kotoba-whisper-bilingual-v1.0",
                device=device,
                model_kwargs=model_kwargs,
                pipeline_class = KotobaWhisperPipeline,
                chunk_length_s=15,
                batch_size=16
            )
            self.__generate_kwargs_translate = {"language": "en", "task": "translate"}
            self.__generate_kwargs_ttranscribe = {"language": "ja", "task": "transcribe"}

        @property
        def required_sample_rate(self) -> int | None:
            return 16000

        def translate(self, audio_data:np.ndarray, text:str) -> TranslateResult:
            reslut = self.__pipe(
                audio_data.astype(np.float16) / float(np.iinfo(np.int16).max),
                generate_kwargs = self.__generate_kwargs_translate)
            r:str = reslut["text"] #type: ignore
            return TranslateResult(r, reslut)

        def get_verbose(self, verbose:int) -> str | None:
            return None

        def transcribe(self, audio_data:np.ndarray) -> TranscribeResult:
            audio = audio_data.astype(np.float16) / float(np.iinfo(np.int16).max)
            sample_rate = self.required_sample_rate
            assert(sample_rate is not None)

            reslut = self.__pipe(
                audio,
                return_timestamps=True,
                generate_kwargs = self.__generate_kwargs_ttranscribe)
            r2 = fix_timestamp(reslut["chunks"], audio, sample_rate) # type: ignore
            reslut["chunks"] = r2 # type: ignore
            if "chunks" in reslut and len(reslut["chunks"]) == 1 and "timestamp" in reslut["chunks"][0]: #type: ignore
                ts = reslut["chunks"][0]["timestamp"] #type: ignore
                if ts[0] == 0.0 and ts[1] == 0.1:
                    raise TranscribeException(f"ノイズ判定:{reslut}") 
            r = reslut["text"] #type: ignore
            if isinstance(r, str):
                return TranscribeResult(r, reslut)
            if isinstance(r, list):
                return TranscribeResult("".join(r), reslut)
            raise ex.ProgramError(f"pipelineから意図しない戻り値型:{type(r)}")


    class TranslateModelTranslateGemma(TranslateModel):
        def __init__(self, device:str, device_index:int, parameter_size:int, target:str) -> None:
            torch_dtype = torch.bfloat16 if device == "cuda" else torch.float32

            if device == "cuda":
                device = f"{device}:{device_index}"
            self.__pipe = pipeline(
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

        def translate(self, audio_data:np.ndarray, text:str) -> TranslateResult:
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
            return TranslateResult(r, output)


