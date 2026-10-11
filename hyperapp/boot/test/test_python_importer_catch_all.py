from types import SimpleNamespace

from hyperapp.boot.python_importer import PythonImporter


source = """
from . import htypes
from .services import pyobj_creg
from .code.system import setup_system
from .explicit import value

result = (htypes.mod.some_t, pyobj_creg, setup_system, value)
"""


class _Recorder:

    def __init__(self, used, prefix=()):
        self._used = used
        self._prefix = prefix

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        path = (*self._prefix, name)
        self._used.add(path)
        return _Recorder(self._used, path)


def test_catch_all():
    used = set()
    imports = {
        '': _Recorder(used),
        'explicit.value': 123,
        }
    module = PythonImporter().import_module('test_catch_all', source, '<test_catch_all>', imports)
    assert [r._prefix for r in module.result[:3]] == [
        ('htypes', 'mod', 'some_t'),
        ('services', 'pyobj_creg'),
        ('code', 'system', 'setup_system'),
        ]
    assert module.result[3] == 123
    assert ('explicit',) not in used
    assert ('code', 'system', 'setup_system') in used
