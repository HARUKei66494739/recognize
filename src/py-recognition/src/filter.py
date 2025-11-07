import numpy 
import io
import numpy
import torchaudio
import scipy
import tensorflow
import tensorflow_hub
import csv
from silero_vad import load_silero_vad, get_speech_timestamps

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

class LowPassFilter(NoiseFilter):
    """
    ノイズフィルタのローパスフィルタ実装
    """
    def __init__(   
        self,
        sampling_rate:int,
        cutoff:int=0,
        cutoff_upper:int=200) -> None:
        super().__init__(sampling_rate)
        self.__cutoff = cutoff
        self.__cutoff_upper = sampling_rate - cutoff_upper

    def filter(self, data:numpy.ndarray):
        pass
        #freq = np.fft.fftfreq(data.size, 1.0 / self.sampling_rate)
        #cutoff = self.__cutoff
        #cutoff_upper = (1 / self.sampling_rate) - cutoff
        #data[((freq > cutoff)&(freq < cutoff_upper))] = 0 + 0j

class HighPassFilter(NoiseFilter):
    """
    ノイズフィルタのハイパスフィルタ実装
    """
    def __init__(   
        self,
        sampling_rate:int,
        cutoff:int=0,
        cutoff_upper:int=200) -> None:
        super().__init__(sampling_rate)
        self.__cutoff = cutoff
        self.__cutoff_upper = cutoff_upper

    def filter(self, data:numpy.ndarray):
        freq = numpy.fft.fftfreq(data.size, 1.0 / self.sampling_rate)
        cutoff = self.__cutoff
        cutoff_upper = self.__cutoff_upper
        #cutoff_upper = (1 / self.sampling_rate) - cutoff
        data[((freq > 0) & (freq < cutoff)) | ((freq < 0) & (freq > -cutoff_upper))] = 0.0

class VadFrame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, bytes:bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


class VoiceActivityDetectorFilter:
    @property
    def mic_pause_duration(self) -> float:
        ...

    def check(self, data:bytes) -> bool:
        ...


class SileroVadFilter(VoiceActivityDetectorFilter):
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

    @property
    def mic_pause_duration(self) -> float:
        return 1.0

    def check(self, data:bytes) -> bool:
        bytes_io = io.BytesIO()
        raw_data = numpy.frombuffer(
            buffer=data, dtype=numpy.int16
        )
        scipy.io.wavfile.write(bytes_io, 16000, raw_data)

        auido, _ = torchaudio.load(bytes_io)
        speech_timestamps = get_speech_timestamps(
            auido,
            self.__model,
            threshold=self.__threshold,
            sampling_rate=self.__sampling_rate)
        return 0 < len(speech_timestamps)
    

class YAMNetVadFilter(VoiceActivityDetectorFilter):
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