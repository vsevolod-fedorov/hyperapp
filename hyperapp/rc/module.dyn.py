from enum import Enum, auto, unique

from .code.path import Path


@unique
class ModuleType(Enum):
    DYNAMIC = auto()
    COMPILED = auto()
    MANUAL = auto()
    TEST = auto()
    FIXTURE = auto()


class Module:

    def __init__(self, type, path, source=None):
        self.type = type
        self.path = path
        self.source = source
        self.project_imports_tgt = None
        self.import_tgt = None
        self.import_alias_tgt = None
        self.module_tgt = None
        self.resource_tgt = None
        # Requirements from the first successful or incomplete import attempt, used for collective classification.
        # None means no accepted first result; an empty tuple means the attempt found no requirements.
        self.first_requirements = None

    @property
    def is_test(self):
        return self.type == ModuleType.TEST
