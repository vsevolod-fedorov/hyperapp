from .code.path import Path


class Module:

    def __init__(self, path, import_tgt):
        self.path = path
        self._import_tgt = import_tgt
