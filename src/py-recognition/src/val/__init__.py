"""
定数モジュール
"""
import importlib.util
import ctypes

from ._enable import \
    ENABLE_METHOD_KODAMA_STREAMING, \
    ENABLE_METHOD_MOONSHINE_VOICE

from .etc import \
    Console, \
    LANGUAGE_CODES, \
    VK

__all__ = [
    Console.__name__,
    "LANGUAGE_CODES",
    "VK",
]


def __is_available_cuda():
    try:
        cuda_device_count = ctypes.c_uint32()
        cuda_device_count.value = 0

        _nvcuda = ctypes.WinDLL("nvcuda.dll")
        _nvcuda.cuInit.restype = ctypes.c_int32
        _nvcuda.cuDeviceGetCount.argtypes = (ctypes.c_uint32,)
        _nvcuda.cuDeviceGetCount.restype = ctypes.c_int32
        _nvcuda.cuDeviceGetCount.argtypes = (ctypes.POINTER(ctypes.c_uint32),)
        _nvcuda.cuInit(0)
        _nvcuda.cuDeviceGetCount(cuda_device_count)
        return 0 < cuda_device_count.value
    except:
        return False


def __support_torch() -> bool:
    if importlib.util.find_spec("transformers") is None:
        return False
    elif importlib.util.find_spec("torch") is None:
        return False
    else:
        return True


def __support_whisper() -> bool:
    if importlib.util.find_spec("whisper") is None:
        return False
    else:
        return True

def __support_whisper_faster() -> bool:
    if importlib.util.find_spec("faster_whisper") is None:
        return False
    else:
        return True

def __support_whisper_kotoba() -> bool:
    return __support_torch()

def __support_moonshine_voice() -> bool:
    if importlib.util.find_spec("moonshine_voice") is None:
        return False
    else:
        return True


def __default_method_value() -> str:
    if __support_whisper_faster():
        return METHOD_VALUE_WHISPER_FASTER
    else:
        return METHOD_VALUE_GOOGLE_DUPLEX


def __choice_method() -> list[str]:
    r = []
    if SUPPORT_LIB_WHISPER:
        r.append(METHOD_VALUE_WHISPER)
    if SUPPORT_LIB_WHISPER_FASTER:
        r.append(METHOD_VALUE_WHISPER_FASTER)
    if SUPPORT_LIB_WHISPER_KOTOBA:
        r.append(METHOD_VALUE_WHISPER_KOTOBA)

    r.append(METHOD_VALUE_GOOGLE)
    r.append(METHOD_VALUE_GOOGLE_DUPLEX)
    r.append(METHOD_VALUE_GOOGLE_MIX)

    if ENABLE_METHOD_MOONSHINE_VOICE and SUPPORT_MOONSHINE_VOICE:
        r.append(METHOD_VALUE_MOONSHINE)
    r.append(METHOD_VALUE_REAZON_SPEECH)
    if ENABLE_METHOD_KODAMA_STREAMING:
        r.append(METHOD_VALUE_KODAMA_STREAMING)
    return r


def __choice_translate() -> list[str]:
    r = [ "" ]
    if SUPPORT_LIB_WHISPER_KOTOBA:
        r.append(TRANSLATE_VALUE_WHISPER_KOTOBA)
        r.append(TRANSLATE_VALUE_GEMMA)
    return r

def __support_silero_vad() -> bool:
    if importlib.util.find_spec("torch") is None:
        return False
    else:
        return SUPPORT_CUDA



SUPPORT_CUDA = __is_available_cuda()
SUPPORT_CUDA_TORCH = SUPPORT_CUDA and __support_torch()
SUPPORT_LIB_WHISPER = __support_whisper()
SUPPORT_LIB_WHISPER_FASTER = __support_whisper_faster()
SUPPORT_LIB_WHISPER_KOTOBA = __support_whisper_kotoba()
SUPPORT_WHISPER = SUPPORT_LIB_WHISPER or SUPPORT_LIB_WHISPER_FASTER or SUPPORT_LIB_WHISPER_KOTOBA
SUPPORT_MOONSHINE_VOICE = __support_moonshine_voice()

VERBOSE_MIN = 0
VERBOSE_INFO = 1
VERBOSE_DEBUG = 2
VERBOSE_TRACE = 3

ARG_NAME_VERBOSE = "--verbose"
ARG_NAME_LOG_FILE = "--log_file"
ARG_NAME_LOG_DIRECTORY = "--log_directory"
ARG_NAME_LOG_ROTATE= "--log_rotate"

ARG_DEFAULT_VERBOSE = str(VERBOSE_INFO)
ARG_DEFAULT_LOG_FILE = "recognize.log"
ARG_DEFAULT_LOG_DIRECTORY = None

ARG_CHOICE_VERBOSE = list(map(lambda x: str(x), [
    VERBOSE_MIN,
    VERBOSE_INFO,
    VERBOSE_DEBUG,
    VERBOSE_TRACE
    ]))

TEST_VALUE_MIC = "mic"
TEST_VALUE_AMBIENT= "mic_ambient"
TEST_VALUE_ILLUMINATE= "illuminate"
ARG_CHOICE_TEST = [
    "",
    TEST_VALUE_MIC,
    TEST_VALUE_AMBIENT,
    TEST_VALUE_ILLUMINATE,
]


MODE_VALUE_BUILT_IN = "builtin"
MODE_VALUE_BROWSER = "browser"
MODE_VALUE_DEFAULT = MODE_VALUE_BUILT_IN
ARG_CHOICE_MODE = [
    MODE_VALUE_BUILT_IN,
    MODE_VALUE_BROWSER,
]

METHOD_VALUE_WHISPER = "whisper"
METHOD_VALUE_WHISPER_FASTER = "faster_whisper"
METHOD_VALUE_WHISPER_KOTOBA = "kotoba_whisper"
METHOD_VALUE_GOOGLE= "google"
METHOD_VALUE_GOOGLE_DUPLEX = "google_duplex"
METHOD_VALUE_GOOGLE_MIX = "google_mix"
METHOD_VALUE_MOONSHINE = "moonshine"
METHOD_VALUE_REAZON_SPEECH = "reazon"
METHOD_VALUE_KODAMA_STREAMING = "kodama"
DEFALUT_METHOD_VALUE = __default_method_value()
ARG_CHOICE_METHOD = __choice_method()

TRANSLATE_VALUE_WHISPER_KOTOBA = "kotoba_whisper"
TRANSLATE_VALUE_GEMMA = "gemma"
DEFALUT_TRANSLATE_VALUE = ""
ARG_CHOICE_TRANSLATE = __choice_translate()

SUBTITLE_VALUE_FILE = "file"
SUBTITLE_VALUE_OBS_WS_V5 = "obs"
ARG_CHOICE_SUBTITLE = [
    "",
    SUBTITLE_VALUE_FILE,
    SUBTITLE_VALUE_OBS_WS_V5,
]


MIC_API_VALUE_MME = "mme"
MIC_API_VALUE_WASAPI = "wasapi"
ARG_CHOICE_MIC_API = [
    MIC_API_VALUE_MME,
    MIC_API_VALUE_WASAPI,
]
MIC_SAMPLE_RATE = 16000
MIC_SAMPLE_WIDTH = 2

VAD_VALUE_WEBRTC = "webrtc"
VAD_VALUE_SILERO = "silero"
VAD_VALUE_YAMNET = "yamnet"
VAD_VALUE_DEFAULT = VAD_VALUE_WEBRTC
ARG_CHOICE_VAD = [
    VAD_VALUE_WEBRTC,
    VAD_VALUE_SILERO,
    VAD_VALUE_YAMNET,
]


CHROME_RECOG_PROC_WEB = "web"
CHROME_RECOG_PROC_LOCAL = "local"
CHROME_RECOG_PROC_DEFAULT = CHROME_RECOG_PROC_LOCAL
ARG_CHOICE_CHROME_RECOG_PROC = [
    CHROME_RECOG_PROC_WEB,
    CHROME_RECOG_PROC_LOCAL,
]


OUT_VALUE_PRINT = "print"
OUT_VALUE_YUKARINETTE = "yukarinette"
OUT_VALUE_YUKACONE = "yukacone"
OUT_VALUE_ILLUMINATE= "illuminate"
OUT_VALUE_OBS= "obs"
OUT_VALUE_FILE= "file"
OUT_VALUE_VRC= "vrc"
ARG_CHOICE_OUT = [
    OUT_VALUE_PRINT,
    OUT_VALUE_YUKARINETTE,
    OUT_VALUE_YUKACONE,
    OUT_VALUE_ILLUMINATE,
    OUT_VALUE_OBS,
    OUT_VALUE_FILE,
    OUT_VALUE_VRC,
]


HTTP_PORT = 40426
RESOURCE_RECOGNIZE_HTML = "src/resources/html.dat"

def get_localhost_address() -> str:
    import socket
    if socket.has_ipv6:
        return "::1"
    else:
        return "127.0.0.1"


def get_recognize_html() -> str:
    from src import ilm_enviroment
    import os

    if ilm_enviroment.is_exe:
        return os.path.join(
            ilm_enviroment.project_root,
            "_internal",
            RESOURCE_RECOGNIZE_HTML)

    else:
        return os.path.join(
            ilm_enviroment.project_root,
            RESOURCE_RECOGNIZE_HTML)


