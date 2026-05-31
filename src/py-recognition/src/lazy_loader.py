import importlib
from lazyasd import lazyobject

from src import ilm_logger
import src.val

_is_torch = False
_is_tenserflow = False


@lazyobject
def whisper():
    return importlib.import_module("whisper")


@lazyobject
def faster_whisper():
    return importlib.import_module("faster_whisper")


@lazyobject
def transformers():
    return importlib.import_module("transformers")


@lazyobject
def torch():
    global _is_torch

    if not _is_torch:
        ilm_logger.print("torchをロードします。この処理は時間がかかることがあります", console=src.val.Console.Yellow, reset_console=True)
        _is_torch = True

    return importlib.import_module("torch")


@lazyobject
def tensorflow():
    global _is_tenserflow

    if not _is_tenserflow:
        ilm_logger.print("tenserflowをロードします。この処理は時間がかかることがあります", console=src.val.Console.Yellow, reset_console=True)
        _is_tenserflow = True

    return importlib.import_module("tensorflow")


@lazyobject
def tensorflow_hub():
    return importlib.import_module("tensorflow_hub")


@lazyobject
def moonshine_voice():
    return importlib.import_module("moonshine_voice")