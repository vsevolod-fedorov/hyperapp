import logging

from ..htypes import (
    ref_t,
    name_mt,
    )
from ..ref import ref_repr
from ..visual_rep import pprint
from ..mapper import Mapper
from .source import TextSource
from .type_module_parser import RecordMtGenerator, parse_type_module_source

log = logging.getLogger(__name__)


class CircularDepError(RuntimeError):
    pass


class _NameToRefMapper(Mapper):

    def __init__(self, mosaic, builtin_name_to_mt, ctx):
        self._mosaic = mosaic
        self._builtin_name_to_mt = builtin_name_to_mt
        self._ctx = ctx

    def map_record(self, t, value, context):
        if t is name_mt:
            return self._resolve_name(value)
        if t is ref_t:
            return self._map_ref(value)
        return value

    def _resolve_name(self, rec):
        try:
            piece = self._builtin_name_to_mt[rec.name]
        except KeyError:
            piece = self._ctx.resolve_name(rec.name)
        log.debug("Name %r is resolved to %r", rec.name, piece)
        return piece

    def _map_ref(self, ref):
        piece = self._mosaic.resolve_ref(ref).value
        log.debug("Ref %s is resolved to %r", ref, piece)
        mapped_piece = self.map(piece)
        log.debug("Ref %s %s is mapped to %r", ref, piece, mapped_piece)
        return self._mosaic.put(mapped_piece)


class TypeModuleLoader(object):

    def __init__(self, builtin_types, mosaic, pyobj_creg):
        self._builtin_types = builtin_types
        self._mosaic = mosaic
        self._pyobj_creg = pyobj_creg

    # registry: module name -> name -> mt piece.
    def load_texts(self, path_to_text, registry):
        name_to_source = {}
        for path, text in path_to_text.items():
            fname = path.split('/')[-1]
            module_name, ext = fname.split('.')
            source = parse_type_module_source(self._builtin_types, self._mosaic, path, text)
            name_to_source[module_name] = source
        for module_name, source in sorted(name_to_source.items()):
            module = self._resolve_module(name_to_source, registry, module_name, [])
            registry[module_name] = module

    def _resolve_module(self, name_to_source, name_to_module, name, dep_stack):
        if name in dep_stack:
            raise CircularDepError("Circular type module dependency: {}".format('->'.join([*dep_stack, name])))
        try:
            return name_to_module[name]  # Already mapped?
        except KeyError:
            pass
        log.debug("Resolve type module: %s", name)
        try:
            source = name_to_source[name]
        except KeyError:
            raise RuntimeError(f"Attempt to import unknown type module: {name}")
        try:
            local_name_dict = self._resolve_module_imports(name_to_source, name_to_module, source, [*dep_stack, name])
        except CircularDepError:
            raise
        except Exception as x:
            raise RuntimeError(f"Error resolving type module {name}: {x}")
        local_type_module = self._map_module_names(name, source, local_name_dict)
        return local_type_module

    def _resolve_module_imports(self, name_to_source, name_to_module, source, dep_stack):
        local_name_dict = {}  # name -> ref
        for import_def in source.import_list:
            imported_module = self._resolve_module(
                name_to_source, name_to_module, import_def.module_name, dep_stack)
            local_name_dict[import_def.target_name] = imported_module[import_def.source_name]
        return local_name_dict

    def _map_module_names(self, name, source, local_name_dict):
        local_type_module = {}
        mapper = _NameToRefMapper(self._builtin_types, self._mosaic, self._pyobj_creg, local_name_dict)
        for typedef in source.typedefs:
            log.debug('Type module loader %r: mapping %r %s:', name, typedef.name, typedef.type)
            mt = typedef.type
            if isinstance(mt, RecordMtGenerator):
                mt = mt.generate(name, typedef.name)
            piece = mapper.map(mt)
            local_type_module[typedef.name] = piece
            local_name_dict[typedef.name] = piece
            log.debug('Type module loader %r: %r is mapped to %r', name, typedef.name, piece)
        return local_type_module


class _ImportDefinition:

    def __init__(self, module_path, name):
        self._module_path = module_path
        self._name = name

    def resolve(self, ctx):
        project_name, path = ctx.find_nearest_module(self._module_path)
        name_tuple = (project_name, path, self._name)
        mt = ctx.resolve(name_tuple)
        sources = {}
        return (mt, sources)


class _Definition:

    def __init__(self, mapper, source_tuple, name, mt):
        self._mapper = mapper
        self._source_tuple = source_tuple
        self._name = name
        self._mt = mt

    def resolve(self, ctx):
        mt = self._mapper.map(self._mt)
        sources = {
            mt: self._source_tuple,
            }
        return (mt, sources)


def load_type_module_definitions(
        pyobj_creg, mosaic, builtin_name_to_type, resource_type_producer, ctx, bytes, source_path):
    module_name = ctx.path[-1]
    text = bytes.decode()
    source_tuple = (ctx.project_name, ctx.path, TextSource(text))
    module_source = parse_type_module_source(mosaic, builtin_name_to_type, text, source_path)
    for rec in module_source.import_list:
        import_def = _ImportDefinition((rec.module_name,), rec.source_name)
        yield (rec.target_name, import_def)
    builtin_name_to_mt = {
        name: pyobj_creg.actor_to_piece(t)
        for name, t in builtin_name_to_type.items()
        }
    mapper = _NameToRefMapper(mosaic, builtin_name_to_mt, ctx)
    for typedef in module_source.typedefs:
        log.debug('%s: Typedef %r: %s', ctx, typedef.name, typedef.type)
        mt = typedef.type
        if isinstance(mt, RecordMtGenerator):
            mt = mt.generate(module_name, typedef.name)
        yield (typedef.name, _Definition(mapper, source_tuple, typedef.name, mt))
