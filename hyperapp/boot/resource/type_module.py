import logging

from ..htypes import (
    ref_t,
    name_mt,
    )
from ..mapper import Mapper
from .source import TextSource
from .type_module_parser import RecordMtGenerator, parse_type_module_source

log = logging.getLogger(__name__)


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


class TypeModuleLoader:

    _ext = '.types'

    def applicable(self, file_path):
        return file_path[-1].endswith(self._ext)

    def file_path_to_path(self, file_path):
        fname = file_path[-1]
        name = fname[:-len(self._ext)]
        return (*file_path[:-1], name)

    def load_definitions(
            self, pyobj_creg, mosaic, builtin_name_to_type, resource_type_producer, ctx, bytes, source_path):
        module_name = ctx.path[-1]
        text = bytes.decode()
        source_tuple = (ctx.project_name, ctx.path, TextSource(text))
        module_source = parse_type_module_source(mosaic, builtin_name_to_type, text, source_path)
        for rec in module_source.import_list:
            import_def = _ImportDefinition(rec.module_name, rec.source_name)
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
