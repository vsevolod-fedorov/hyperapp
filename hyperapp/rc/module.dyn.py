from enum import Enum, auto, unique

from .code.path import Path


@unique
class ModuleType(Enum):
    COMPILED = auto()
    MANUAL = auto()
    TEST = auto()
    FIXTURE = auto()


class Module:

    def __init__(self, type, path, source=None):
        self.type = type
        self.path = path
        self.source = source
        self.import_tgt = None
        self.import_alias_tgt = None
        self.module_tgt = None
        self.resource_tgt = None
