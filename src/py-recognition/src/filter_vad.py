
import io
import numpy 
import scipy
import csv
import webrtcvad
from silero_vad import load_silero_vad, get_speech_timestamps

import src.interface as inf
from src.lazy_loader import torch, tensorflow, tensorflow_hub


class VadFrame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, bytes:bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


class WebRtcVadFilter(inf.VoiceActivityDetectorFilter):
    """
    WebRtcVADフィルタ
    """
    def __init__(   
        self,
        sampling_rate:int,
        vad_mode:int):
        self.__vad = webrtcvad.Vad(vad_mode)
        self.__sampling_rate = sampling_rate

    @property
    def mic_pause_duration(self) -> float:
        return 0.4

    def check(self, data:bytes) -> bool:
        frame_duration_ms = 30
        return WebRtcVadFilter._check(
            self.__sampling_rate,
            frame_duration_ms, frame_duration_ms * 10,
            self.__vad,
            list(WebRtcVadFilter._frame_generator(frame_duration_ms, data, self.__sampling_rate)))


    @staticmethod
    def _frame_generator(frame_duration_ms:int, audio:bytes, sample_rate:int):
        """Generates audio frames from PCM audio data.

        Takes the desired frame duration in milliseconds, the PCM data, and
        the sample rate.

        Yields Frames of the requested duration.
        """
        n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
        offset = 0
        timestamp = 0.0
        duration = (float(n) / sample_rate) / 2.0
        while offset + n < len(audio):
            yield VadFrame(audio[offset:offset + n], timestamp, duration)
            timestamp += duration
            offset += n

    @staticmethod
    def _check(
        sample_rate:int,
        frame_duration_ms:int,
        padding_duration_ms:int,
        vad:webrtcvad.Vad,
        frames: list[VadFrame],
        voice_trigger_on_thres:float=0.9,
        voice_trigger_off_thres: float=0.1) -> bool:
        # ガードするフレーム数
        num_padding_frames = int(padding_duration_ms / frame_duration_ms)

        # バッファ(リングバッファではなくする)
        frame_buffer = []
        for frame in frames:
            is_speech = vad.is_speech(frame.bytes, sample_rate)
            frame_buffer.append((frame, is_speech))

            # 過去フレームのうち音声判定数を取得
            # 過去を見る数はnum_padding_frames個
            num_voiced = len([f for f, speech in frame_buffer[-num_padding_frames:] if speech])

            # 9割以上が音声の場合は音声にトリガする(立ち上がり)
            if num_voiced > voice_trigger_on_thres * num_padding_frames:
                return True
        return False


class SileroVadFilter(inf.VoiceActivityDetectorFilter):
    """
    Silero-VADフィルタ
    """

    def __init__(   
        self,
        sampling_rate:int,
        threshold):

        self.__model = load_silero_vad()
        self.__sampling_rate = sampling_rate
        self.__threshold = threshold

        torch.tensor([1, 2,3 ])

    @property
    def mic_pause_duration(self) -> float:
        return 1.0

    def check(self, data:bytes) -> bool:
        bytes_io = io.BytesIO()
        raw_data = numpy.frombuffer(
            buffer=data, dtype=numpy.int16
        )
        scipy.io.wavfile.write(bytes_io, 16000, raw_data)

        auido = torch.from_numpy(raw_data.astype(numpy.float16) / float(numpy.iinfo(numpy.int16).max))
        speech_timestamps = get_speech_timestamps(
            auido,
            self.__model,
            threshold=self.__threshold,
            sampling_rate=self.__sampling_rate)
        return 0 < len(speech_timestamps)

class YAMNetVadFilter(inf.VoiceActivityDetectorFilter):
    """
    YAMNet-VADフィルタ
    """

    def __init__(   
        self,
        sampling_rate:int):

        self.__model = tensorflow_hub.load("https://tfhub.dev/google/yamnet/1")
        self.__classes = [
            "Speech",
            "Speech synthesizer",
            "Narration, monologue"
        ]

        # YAMNetクラス名一覧取得
        with tensorflow.io.gfile.GFile(self.__model.class_map_path().numpy()) as csvfile:
            reader = csv.DictReader(csvfile)
            self.__class_names = list(map(lambda x: x["display_name"], reader))

    @property
    def mic_pause_duration(self) -> float:
        return 0.4

    def check(self, data:bytes) -> bool:
        wav = numpy.frombuffer(data, dtype=numpy.int16)
        waveform = wav / tensorflow.int16.max

        scores, _, _ = self.__model(waveform)
        scores_np = scores.numpy()

        class_scores = {cls: sc for cls, sc in zip(self.__class_names, scores_np.mean(axis=0))}

        return 0.1 < sum(map(lambda x: class_scores[x], self.__classes))