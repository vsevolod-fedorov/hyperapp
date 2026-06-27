import codecs
import inspect
import logging
import importlib
import sys
from collections import defaultdict
from pathlib import Path

from hyperapp.boot.htypes.python_module import import_rec_t, python_module_t, import_rec_def_t, python_module_def_t
from hyperapp.boot.htypes import HException
from hyperapp.boot.dict_decoder import NamedPairsDictDecoder
from hyperapp.boot.dict_encoder import NamedPairsDictEncoder
from hyperapp.boot.python_importer import ROOT_PACKAGE, PythonModuleImportError

log = logging.getLogger(__name__)


class PythonModuleResourceImportError(Exception):

    def __init__(self, message, original_error, import_name, module_name):
        super().__init__(message)
        self.original_error = original_error
        self.import_name = import_name
        self.module_name = module_name


class PythonModuleResourceType:

    name = 'python_module'
    resource_t = python_module_t
    definition_t = python_module_def_t

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<ResourceType: {self.name!r}>"

    def from_dict(self, data):
        decoder = NamedPairsDictDecoder()
        return decoder.decode_dict(self.definition_t, data)

    def to_dict(self, definition):
        encoder = NamedPairsDictEncoder()
        return encoder.encode(definition)

    def resolve(self, definition, ctx):
        import_list = tuple(
            import_rec_t(
                full_name=rec.full_name,
                resource=ctx.resolve_to_ref(rec.resource),
                )
            for rec in definition.import_list
            )
        text, path, sources = ctx.get_text(definition.file_name)
        piece = python_module_t(
            module_name=definition.module_name,
            source=text,
            file_path='/'.join(path),  # TODO: Add project to path.
            import_list=import_list,
            )
        return (piece, sources)

    def reverse_resolve(self, resource, resolver, resource_dir):
        import_list = tuple(
            import_rec_def_t(
                full_name=rec.full_name,
                resource=resolver(rec.resource),
                )
            for rec in resource.import_list
            )
        return python_module_def_t(
            module_name=resource.module_name,
            file_name=str(Path(resource.file_path).name),
            import_list=import_list,
            )


class _ObjectLoader:
    is_package = False

    def __init__(self, obj):
        self._obj = obj

    def create_module(self, spec):
        return self._obj

    def exec_module(self, module):
        pass


def make_module_name(mosaic, module):
    module_ref = mosaic.put(module)
    hash_hex = codecs.encode(module_ref.hash[:10], 'hex').decode()
    return f'{ROOT_PACKAGE}.{module_ref.hash_algorithm}_{hash_hex}'

                
def python_module_pyobj(piece, mosaic, python_importer, pyobj_creg):
    module_name = make_module_name(mosaic, piece)
    if module_name in sys.modules:
        raise RuntimeError(f"Error: module {module_name} is aleady imported")
    try:
        loaders = {
            f'{module_name}.{rec.full_name}': _ObjectLoader(pyobj_creg.invite(rec.resource))
            for rec in piece.import_list
            }
        return python_importer.import_module(module_name, piece.source, piece.file_path, loaders)
    except HException:
        raise
    except PythonModuleImportError as x:
        raise PythonModuleResourceImportError(str(x), x.original_error, x.import_name, piece.module_name) from x
