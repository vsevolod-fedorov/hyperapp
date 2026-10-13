from enum import Enum, auto, unique

from .code.path import Path


@unique
class ModuleType(Enum):
    COMPILED = auto()
    MANUAL = auto()
    TEST = auto()
    FIXTURE = auto()


class Module:

    def __init__(self, type, path, import_tgt=None):
        self.type = type
        self.path = path
        self._import_tgt = import_tgt
