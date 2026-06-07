import logging
from pathlib import Path
from unittest.mock import Mock

import pytest

from hyperapp.boot.htypes import tInt, field_mt, record_mt
from hyperapp.boot.resource.record_mt_resource_type import field_def_mt, record_def_mt

log = logging.getLogger(__name__)


pytest_plugins = [
    'hyperapp.boot.test.services',
    'hyperapp.boot.resource.test.services',
    ]


def test_definition_type(resource_type_producer):
    resource_t = record_mt
    resource_type = resource_type_producer(resource_t)
    assert resource_type.definition_t is record_def_mt


def test_from_dict(resource_type_producer):
    resource_t = record_mt
    resource_type = resource_type_producer(resource_t)
    definition_dict = {
        'name': 'sample_name',
        'base': 'sample_base',
        'fields': {
            'an_int': 'legacy_type.builtin:int',
            },
        }
    definition = resource_type.from_dict(definition_dict)
    log.info("definition: %r", definition)
    assert definition == record_def_mt(
        name='sample_name',
        base='sample_base',
        fields=(
            field_def_mt('an_int', 'legacy_type.builtin:int'),
            ),
        )


def mock_ctx(names):
    def resolve_to_ref(name):
        return names[name]

    return Mock(
        path=('sample_module',),
        resolve_to_ref=resolve_to_ref,
        resolve_to_ref_opt=resolve_to_ref,
        )


def test_resolve(mosaic, pyobj_creg, resource_type_producer):
    resource_t = record_mt
    resource_type = resource_type_producer(resource_t)

    sample_base = record_mt(
        module_name='sample_base_module_name',
        name='sample_base_name',
        base=None,
        fields=(),
        )

    names = {
        'legacy_type.builtin:int': pyobj_creg.actor_to_ref(tInt),
        'sample_base': mosaic.put(sample_base),
        }
    ctx = mock_ctx(names)

    definition = resource_type.definition_t(
        name='sample_name',
        base='sample_base',
        fields=(
            field_def_mt('an_int', 'legacy_type.builtin:int'),
            ),
        )

    resource, sources = resource_type.resolve(definition, ctx)
    log.info('Resolved resource: %r', resource)

    assert resource == record_mt(
        module_name='sample_module',
        name='sample_name',
        base=mosaic.put(sample_base),
        fields=(
            field_mt('an_int', pyobj_creg.actor_to_ref(tInt)),
            ),
        )


def test_reverse_resolve(mosaic, pyobj_creg, resource_type_producer):
    pass  # TODO
