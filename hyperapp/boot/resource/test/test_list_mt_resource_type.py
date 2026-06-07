import logging
from pathlib import Path
from unittest.mock import Mock

import pytest

from hyperapp.boot.htypes import tInt, list_mt
from hyperapp.boot.resource.list_mt_resource_type import list_def_mt

log = logging.getLogger(__name__)


pytest_plugins = [
    'hyperapp.boot.test.services',
    'hyperapp.boot.resource.test.services',
    ]

TEST_DIR = Path(__file__).parent.resolve()
TEST_RESOURCES_DIR = TEST_DIR / 'test_resources'


@pytest.fixture
def test_resources_dir():
    return TEST_RESOURCES_DIR


def mock_ctx(names):
    def resolve_to_ref(name):
        return names[name]

    return Mock(resolve_to_ref=resolve_to_ref)


def test_definition_type(resource_type_producer):
    resource_t = list_mt
    resource_type = resource_type_producer(resource_t)
    assert resource_type.definition_t is list_def_mt


def test_from_dict(resource_type_producer):
    resource_t = list_mt
    resource_type = resource_type_producer(resource_t)
    definition_dict = {
        'element': 'legacy_type.builtin:int',
        }
    definition = resource_type.from_dict(definition_dict)
    log.info("definition: %r", definition)
    assert definition == list_def_mt(
        element='legacy_type.builtin:int',
        )


def test_resolve(mosaic, pyobj_creg, resource_type_producer):
    resource_t = list_mt
    resource_type = resource_type_producer(resource_t)

    names = {
        'legacy_type.builtin:int': pyobj_creg.actor_to_ref(tInt),
        }
    ctx = mock_ctx(names)

    definition = resource_type.definition_t(
        element='legacy_type.builtin:int',
        )

    resource, sources = resource_type.resolve(definition, ctx)
    log.info('Resolved resource: %r', resource)

    assert resource == list_mt(
        element=pyobj_creg.actor_to_ref(tInt),
        )


def test_reverse_resolve(mosaic, pyobj_creg, resource_type_producer):
    resource_t = list_mt
    resource_type = resource_type_producer(resource_t)

    names = {
        'legacy_type.builtin:int': pyobj_creg.actor_to_ref(tInt),
        }
    reverse_names = {
        value: key for key, value in names.items()
        }
    def reverse_resolve_name(name):
        return reverse_names[name]

    resource = resource_t(
        element=pyobj_creg.actor_to_ref(tInt),
        )

    definition = resource_type.reverse_resolve(resource, reverse_resolve_name, TEST_RESOURCES_DIR)
    log.info('Resolved definition: %r', definition)

    assert definition == resource_type.definition_t(
        element='legacy_type.builtin:int',
        )
