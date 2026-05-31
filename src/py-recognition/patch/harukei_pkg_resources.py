import packaging.version
import importlib.metadata

class Wrapper:
    def __init__(self, module:str) -> None:
         self.__module = module

    @property
    def version(self):
        return importlib.metadata.version(self.__module)


def get_distribution(module:str):
    return Wrapper(module)


def parse_version(v):
    return packaging.version.parse(v)