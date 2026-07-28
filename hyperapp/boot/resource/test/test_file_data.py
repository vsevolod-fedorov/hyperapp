import logging
import yaml
from pathlib import Path
from unittest.mock import Mock

import pytest

from hyperapp.boot.htypes.file_data import (
    file_data_t,
    file_data_def_t,
    )
from hyperapp.boot.resource.file_data import FileDataType

log = logging.getLogger(__name__)


pytest_plugins = [
    'hyperapp.boot.test.services',
    'hyperapp.boot.resource.test.services',
    ]

TEST_DIR = Path(__file__).parent.resolve()
TEST_RESOURCES_DIR = TEST_DIR / 'resources' / 'python_module_type'


@pytest.fixture
def resource_type_reg():
    reg = {}
    reg[file_data_t] = FileDataType()
    return reg


def test_definition_type(resource_type_producer):
    resource_t = file_data_t
    resource_type = resource_type_producer(resource_t)
    assert resource_type.definition_t is file_data_def_t


def test_from_dict(resource_type_producer):
    resource_t = file_data_t
    resource_type = resource_type_producer(resource_t)
    definition_dict = {
        'file_name': 'sample_data.data',
        }
    definition = resource_type.from_dict(definition_dict)
    log.info("definition: %r", definition)
    assert definition == resource_type.definition_t(
        file_name='sample_data.data',
        )


def mock_ctx(project_name, names, data):
    def resolve_to_ref(name):
        return names[name]
    def get_bytes(file_name):
        path = (file_name,)
        sources = {
            data: (project_name, path, None)
            }
        return (data, project_name, path, sources)

    return Mock(
        resolve_to_ref=resolve_to_ref,
        get_bytes=get_bytes,
    )


def test_resolve(mosaic, resource_type_producer):
    resource_t = file_data_t
    resource_type = resource_type_producer(resource_t)

    project_name = 'sample-project'
    data = b'sample data'
    names = {
        'resource_1': mosaic.put('resource 1'),
        'resource_2': mosaic.put('resource 2'),
        'resource_3': mosaic.put('resource 3'),
        }
    ctx = mock_ctx(project_name, names, data)

    definition = resource_type.definition_t(
        file_name='sample_data.data',
        )

    resource, sources = resource_type.resolve(definition, ctx)
    log.info('Resolved resource: %r', resource)

    assert resource == resource_t(
        data=data,
        )
    assert sources[resource.data][:2] == (project_name, ('sample_data.data',))


def test_reverse_resolve(mosaic, resource_type_producer):
    pass  # TODO
