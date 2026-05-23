import logging
from collections import namedtuple

import yaml


log = logging.getLogger(__name__)


_Definition = namedtuple('_Definition', 'type value')


def _load_yaml(bytes, file_path):
    loader = yaml.SafeLoader(bytes)
    loader.name = file_path
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
    resource_t_piece = ctx.resolve(type_name)
    resource_t = pyobj_creg.animate(resource_t_piece)
    definition_t = resource_type_producer(resource_t)
    try:
        definition = definition_t.from_dict(value_dict)
    except Exception as x:
        raise RuntimeError(f"{ctx}: Error resolving definition {name}: {x}")
    return _Definition(definition_t, definition)


def load_resource_module_definitions(pyobj_creg, resource_type_producer, ctx, bytes, file_path):
    data = _load_yaml(bytes, file_path)
    for name, contents in data.get('definitions', {}).items():
        yield (name, _load_definition(pyobj_creg, resource_type_producer, ctx, name, contents))
