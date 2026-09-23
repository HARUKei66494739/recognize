
import src.val

from .common import \
    RecognizeMicrophoneConfig, \
    DefaultMicrophoneConfig, \
    TranscribeException
from .google import \
    GoogleMicrophoneConfig, \
    RecognitionModelGoogle, \
    RecognitionModelGoogleDuplex, \
    RecognitionModelGoogleMix
from .etc import \
    ReazonSpeechMicrophoneConfig, \
    RecognitionModelChrome, \
    RecognitionModelReazonSpeechK2, \
    RecognitionModelKodamaStreaming

__all__ = [
    RecognizeMicrophoneConfig.__name__,
    DefaultMicrophoneConfig.__name__,
    TranscribeException.__name__,

    GoogleMicrophoneConfig.__name__,
    RecognitionModelGoogle.__name__,
    RecognitionModelGoogleDuplex.__name__,
    RecognitionModelGoogleMix.__name__,

    ReazonSpeechMicrophoneConfig.__name__,
    RecognitionModelChrome.__name__,
    RecognitionModelReazonSpeechK2.__name__,
    RecognitionModelKodamaStreaming.__name__,
]

if src.val.SUPPORT_LIB_WHISPER:
    from .torch import RecognitionModelWhisper
    __all__.append(RecognitionModelWhisper.__name__)

if src.val.SUPPORT_LIB_WHISPER_FASTER:
    from .torch import RecognitionModelWhisperFaster
    __all__.append(RecognitionModelWhisperFaster.__name__)

if src.val.SUPPORT_CUDA_TORCH:
    from .torch import RecognizeAndTranslateModelKotobaWhisper, \
        TranslateModelTranslateGemma
    __all__.append(RecognizeAndTranslateModelKotobaWhisper.__name__)
    __all__.append(TranslateModelTranslateGemma.__name__)

if src.val.SUPPORT_MOONSHINE_VOICE:
    from .moonshine import RecognitionModelMoonShine
    __all__.append(RecognitionModelMoonShine.__name__)