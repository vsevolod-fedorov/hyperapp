import logging

import pytest

from hyperapp.boot.resource.source import ResourceModuleSource

log = logging.getLogger(__name__)


pytest_plugins = [
    'hyperapp.boot.test.services',
    'hyperapp.boot.resource.test.services',
    'hyperapp.boot.resource.test.loader',
    ]


@pytest.fixture
def resources_dir(test_dir):
    return test_dir / 'resources' / 'resource_module'


def test_primitive_types(loader):
    _, sources = loader({'primitive': 'primitive'})
    assert sources[123] == ('primitive', ('sample',), ResourceModuleSource('an_int'))


def test_resolve_local(web, loader):
    resources, sources = loader({'a-project': 'resolve_local'})
    attr = resources['a-project', ('sample',), 'an_attribute']
    object = web.summon(attr.object)
    assert object == 123


def test_resolve_in_project(web, loader):
    resources, sources = loader({'a-project': 'resolve_in_project'})
    attr = resources['a-project', ('module_2',), 'an_attribute']
    object = web.summon(attr.object)
    assert object == 123
    assert resources['a-project', ('module_1',), 'an_int'] == 123


def test_resolve_between_projects(web, loader):
    projects = {
        'project-1': 'resolve_between_projects/project_1',
        'project-2': 'resolve_between_projects/project_2',
        }
    resources, sources = loader(projects)
    attr = resources['project-2', ('module_2',), 'an_attribute']
    object = web.summon(attr.object)
    assert object == 123
    assert resources['project-1', ('subdir', 'module_1'), 'an_int'] == 123
    assert sources[attr] == ('project-2', ('module_2',), ResourceModuleSource('an_attribute'))
