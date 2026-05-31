import logging

import yaml

from .source import ResourceModuleSource


log = logging.getLogger(__name__)


class _Definition:

    def __init__(self, name, type, value):
        self._name = name
        self._type = type
        self._value = value

    def resolve(self, ctx):
        piece, type_sources = self._type.resolve(self._value, ctx)
        sources = {
            **type_sources,
            piece: (ctx.project_name, ctx.path, ResourceModuleSource(self._name)),
            }
        return (piece, sources)


def _load_yaml(bytes, source_path):
    loader = yaml.SafeLoader(bytes)
    loader.name = source_path
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def _load_definition(pyobj_creg, resource_type_producer, ctx, name, data):
    log.debug("%s: Load %r: %s", ctx, name, data)
    try:
        type_name = data['type']
        value_dict = data['value']
    except KeyError as x:
        raise RuntimeError(f"{ctx}: definition {name!r} has no {x.args[0]!r} attribute")
    resource_t_piece = ctx.resolve_name(type_name)
    resource_t = pyobj_creg.animate(resource_t_piece)
    definition_t = resource_type_producer(resource_t)
    try:
        definition = definition_t.from_dict(value_dict)
    except Exception as x:
        raise RuntimeError(f"{ctx}: Error resolving definition {name}: {x}")
    return _Definition(name, definition_t, definition)


def load_resource_module_definitions(
        pyobj_creg, mosaic, builtin_name_to_type, resource_type_producer, ctx, bytes, source_path):
    data = _load_yaml(bytes, source_path)
    for name, contents in data.get('definitions', {}).items():
        yield (name, _load_definition(pyobj_creg, resource_type_producer, ctx, name, contents))
