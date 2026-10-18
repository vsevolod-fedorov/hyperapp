from . import htypes
from .services import (
    pyobj_creg,
    )


# Raised when an imported object is used beyond getting its attributes.
# Its real value is unknown at import-job time, so the module can not be imported completely yet.
class IncompleteImportError(Exception):

    def __init__(self, path):
        super().__init__(f"Imported object is used: {'.'.join(path)}")
        self.path = path


class _Recorder:

    def __init__(self, used_imports, prefix=()):
        self._prefix = prefix
        self._used_imports = used_imports  # name tuple set.

    def __repr__(self):
        return f"<_Recorder: {'.'.join(self._prefix)}>"

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        path = (*self._prefix, name)
        return self._get_resource(path)

    def _get_resource(self, path):
        self._used_imports.add(path)
        return _Recorder(self._used_imports, path)

    @property
    def used_imports(self):
        return self._used_imports


def _raise_incomplete(self, *args, **kw):
    raise IncompleteImportError(self._prefix)


# Special methods are looked up on the type, bypassing __getattr__, so each one is set explicitly.
# Left working, because infrastructure uses them on the recorder itself:
# - string conversion: the code registry logs every animated object with str();
# - identity hash and equality: the cached code registry keeps a reverse cache keyed by actor;
# - attribute setting: the import machinery sets __spec__ and the like on the module object.
_INCOMPLETE_METHODS = [
    '__call__', '__mro_entries__', '__instancecheck__', '__subclasscheck__',
    '__getitem__', '__setitem__', '__delitem__', '__len__', '__iter__', '__reversed__', '__contains__',
    '__bool__', '__lt__', '__le__', '__gt__', '__ge__',
    '__bytes__', '__index__', '__int__', '__float__', '__complex__',
    '__divmod__', '__rdivmod__', '__neg__', '__pos__', '__abs__', '__invert__',
    '__round__', '__trunc__', '__floor__', '__ceil__',
    '__enter__', '__exit__', '__aenter__', '__aexit__', '__await__', '__aiter__',
    ]
for _op in [
        'add', 'sub', 'mul', 'matmul', 'truediv', 'floordiv', 'mod', 'pow',
        'lshift', 'rshift', 'and', 'xor', 'or',
        ]:
    _INCOMPLETE_METHODS += [f'__{_op}__', f'__r{_op}__', f'__i{_op}__']
for _name in _INCOMPLETE_METHODS:
    setattr(_Recorder, _name, _raise_incomplete)


def register_import_recorder_pyobj():
    pyobj_creg.update_resolved_config({
        htypes.import_recorder.import_recorder: recorder_from_piece,
        })


def recorder_from_piece(piece):
    used_imports = set()
    return _Recorder(used_imports)
