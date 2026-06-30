import logging
import yaml
from pathlib import Path
from unittest.mock import Mock

import pytest

from hyperapp.boot.htypes.python_module import (
    python_module_t,
    python_module_def_t,
    imports_t,
    imports_def_t,
    import_rec_t,
    import_rec_def_t,
    )
from hyperapp.boot.resource.python_module import PythonModuleResourceType

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
    reg[python_module_t] = PythonModuleResourceType()
    return reg


def test_definition_type(resource_type_producer):
    resource_t = python_module_t
    resource_type = resource_type_producer(resource_t)
    assert resource_type.definition_t is python_module_def_t


def test_from_dict(resource_type_producer):
    resource_t = python_module_t
    resource_type = resource_type_producer(resource_t)
    definition_dict = {
        'module_name': 'sample module',
        'file_name': 'sample_module.dyn.py',
        'imports': {
            'pyobj': [],
            'raw': [
                {'full_name': 'some.used_1', 'resource': 'some.resource_1'},
                ],
            },
        }
    definition = resource_type.from_dict(definition_dict)
    log.info("definition: %r", definition)
    assert definition == resource_type.definition_t(
        module_name='sample module',
        file_name='sample_module.dyn.py',
        imports=imports_def_t(
            pyobj=(),
            raw=(
                import_rec_def_t('some.used_1', 'some.resource_1'),
                ),
            )
        )


def mock_ctx(project_name, names, text):
    def resolve_to_ref(name):
        return names[name]
    def get_text(file_name):
        path = (file_name,)
        sources = {
            text: (project_name, path, None)
            }
        return (text, project_name, path, sources)

    return Mock(
        resolve_to_ref=resolve_to_ref,
        get_text=get_text,
    )


def test_resolve(mosaic, resource_type_producer):
    resource_t = python_module_t
    resource_type = resource_type_producer(resource_t)

    project_name = 'sample-project'
    source = TEST_RESOURCES_DIR.joinpath('sample_module.dyn.py').read_text()
    names = {
        'resource_1': mosaic.put('resource 1'),
        'resource_2': mosaic.put('resource 2'),
        'resource_3': mosaic.put('resource 3'),
        }
    ctx = mock_ctx(project_name, names, source)

    definition = resource_type.definition_t(
        module_name='sample module',
        file_name='sample_module.dyn.py',
        imports=imports_def_t(
            pyobj=(
                import_rec_def_t('some.used_1', 'resource_1'),
                import_rec_def_t('some.used_2', 'resource_2'),
                ),
            raw=(
                import_rec_def_t('some.used_3', 'resource_3'),
                ),
            ),
        )

    resource, sources = resource_type.resolve(definition, ctx)
    log.info('Resolved resource: %r', resource)

    assert resource == resource_t(
        module_name='sample module',
        source=source,
        imports=imports_t(
            pyobj=(
                import_rec_t('some.used_1', names['resource_1']),
                import_rec_t('some.used_2', names['resource_2']),
                ),
            raw=(
                import_rec_t('some.used_3', names['resource_3']),
                ),
            ),
        )
    assert sources[resource.source][:2] == (project_name, ('sample_module.dyn.py',))


def test_reverse_resolve(mosaic, resource_type_producer):
    resource_t = python_module_t
    resource_type = resource_type_producer(resource_t)

    names = {
        'resource_1': mosaic.put('resource 1'),
        'resource_2': mosaic.put('resource 2'),
        }
    reverse_names = {
        value: key for key, value in names.items()
        }
    def reverse_resolve_name(name):
        return reverse_names[name]

    resource = resource_t(
        module_name='sample module',
        source=TEST_RESOURCES_DIR.joinpath('sample_module.dyn.py').read_text(),
        imports=imports_t(
            pyobj=(
                import_rec_t('some.used_1', names['resource_1']),
                import_rec_t('some.used_2', names['resource_2']),
                ),
            raw=(),
            ),
        )

    definition = resource_type.reverse_resolve(resource, reverse_resolve_name, TEST_RESOURCES_DIR)
    log.info('Resolved definition: %r', definition)

    assert definition == resource_type.definition_t(
        module_name='sample module',
        file_name='',
        imports=imports_def_t(
            pyobj=(
                import_rec_def_t('some.used_1', 'resource_1'),
                import_rec_def_t('some.used_2', 'resource_2'),
                ),
            raw=(),
            ),
        )
