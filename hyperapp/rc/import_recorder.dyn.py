from . import htypes
from .services import (
    pyobj_creg,
    )


class _Recorder:

    def __init__(self, used_imports, prefix=()):
        self._prefix = prefix
        self._used_imports = used_imports  # name tuple set.

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        path = (*self._prefix, name)
        return self._get_resource(path)

    def _get_resource(self, path):
        self._used_imports.add(path)
        return _Recorder(self._used_imports, path)


def register_import_recorder_pyobj():
    pyobj_creg.update_resolved_config({
        htypes.import_recorder.import_recorder: recorder_from_piece,
        })


def recorder_from_piece(piece):
    used_imports = set()
    return _Recorder(used_imports)
