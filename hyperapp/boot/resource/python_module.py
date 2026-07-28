import codecs
import logging
import sys

from ..htypes.python_module import (
    import_rec_t,
    python_module_t,
    imports_t,
    imports_def_t,
    import_rec_def_t,
    python_module_def_t,
    )
from ..htypes import HException
from ..dict_decoder import NamedPairsDictDecoder
from ..dict_encoder import NamedPairsDictEncoder
from ..python_importer import DynModuleImportError

log = logging.getLogger(__name__)


class DynModuleResourceImportError(Exception):

    def __init__(self, message, original_error, tb, import_name, module_name):
        super().__init__(message)
        self.original_error = original_error
        self.tb = tb
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
        return decoder.decode_dict(data, self.definition_t)

    def to_dict(self, definition):
        encoder = NamedPairsDictEncoder()
        return encoder.encode_dict(definition)

    def resolve(self, definition, ctx):
        pyobj_imports = tuple(
            import_rec_t(
                full_name=rec.full_name,
                resource=ctx.resolve_to_ref(rec.resource),
                )
            for rec in definition.imports.pyobj
            )
        raw_imports = tuple(
            import_rec_t(
                full_name=rec.full_name,
                resource=ctx.resolve_to_ref(rec.resource),
                )
            for rec in definition.imports.raw
            )
        text, project_name, path, sources = ctx.get_text(definition.file_name)
        piece = python_module_t(
            module_name=definition.module_name,
            source=text,
            imports=imports_t(
                pyobj=pyobj_imports,
                raw=raw_imports,
                ),
            )
        return (piece, sources)

    def reverse_resolve(self, resource, resolver, resource_dir):
        pyobj_imports = tuple(
            import_rec_def_t(
                full_name=rec.full_name,
                resource=resolver(rec.resource),
                )
            for rec in resource.imports.pyobj
            )
        raw_imports = tuple(
            import_rec_def_t(
                full_name=rec.full_name,
                resource=resolver(rec.resource),
                )
            for rec in resource.imports.raw
            )
        return python_module_def_t(
            module_name=resource.module_name,
            file_name='',  # TODO
            imports=imports_def_t(
                pyobj=pyobj_imports,
                raw=raw_imports,
                ),
            )


def make_module_name(mosaic, module):
    module_ref = mosaic.put(module)
    hash_hex = codecs.encode(module_ref.hash[:10], 'hex').decode()
    return f'{module_ref.hash_algorithm}_{hash_hex}'


def python_module_pyobj(piece, mosaic, web, python_importer, source_path, pyobj_creg):
    module_name = make_module_name(mosaic, piece)
    file_path = source_path.get(piece)
    if not file_path:
        file_path = f'hyperapp://{module_name}'
    if module_name in sys.modules:
        raise RuntimeError(f"Error: module {module_name} is aleady imported")
    try:
        pyobj_imports = {
            rec.full_name: pyobj_creg.invite(rec.resource)
            for rec in piece.imports.pyobj
            }
        raw_imports = {
            rec.full_name: web.summon(rec.resource)
            for rec in piece.imports.raw
            }
        imports = {**pyobj_imports, **raw_imports}
        return python_importer.import_module(module_name, piece.source, file_path, imports)
    except HException:
        raise
    except DynModuleImportError as x:
        raise DynModuleResourceImportError(
            str(x), x.original_error, x.tb, module_name, piece.module_name) from x
