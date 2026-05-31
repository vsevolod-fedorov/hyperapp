import logging
from pathlib import Path

import pytest

from hyperapp.boot.htypes import tInt, tString, TRecord
from hyperapp.boot.htypes.python_module import python_module_t
from hyperapp.boot.resource.loader import load_file_tree, load_resources
from hyperapp.boot.resource.source import ResourceModuleSource, TextSource
from hyperapp.boot import cdr_coders  # self-registering

log = logging.getLogger(__name__)


pytest_plugins = [
    'hyperapp.boot.test.services',
    'hyperapp.boot.resource.test.services',
    ]

TEST_DIR = Path(__file__).parent.resolve()
RESOURCES_ROOT = TEST_DIR / 'resources'


@pytest.fixture
def resources_root():
    return RESOURCES_ROOT


@pytest.fixture
def loader(pyobj_creg, mosaic, builtin_name_to_type, resource_type_producer, resources_root):
    def load(project_to_path):
        project_to_files = {
            name: load_file_tree(resources_root / path)
            for name, path in project_to_path.items()
            }
        resources, source_dict = load_resources(pyobj_creg, mosaic, builtin_name_to_type, resource_type_producer, project_to_files)
        for name, piece in resources.items():
            log.info("Loaded piece: %s -> %r", name, piece)
        for piece, project_name_path_source in source_dict.items():
            log.info("Loaded source: %r -> %r", piece, project_name_path_source)
        return resources, source_dict
    return load


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


def test_python_module(loader):
    resources, sources = loader({'a-project': 'python_module'})
    piece = resources['a-project', ('sample',), 'a_module.module']
    assert isinstance(piece, python_module_t)
    assert "Hello from" in piece.source
    assert sources[piece.source] == ('a-project', ('a_module.dyn.py',), TextSource(piece.source))
    assert sources[piece] == ('a-project', ('sample',), ResourceModuleSource('a_module.module'))


def test_python_module_fn(pyobj_creg, loader):
    resources, sources = loader({'a-project': 'python_module_fn'})
    piece = resources['a-project', ('sample',), 'fn']
    fn = pyobj_creg.animate(piece)
    result = fn()
    assert result == 123


def test_python_module_import(pyobj_creg, loader):
    resources, sources = loader({'a-project': 'python_module_import'})
    piece = resources['a-project', ('sample',), 'main']
    main = pyobj_creg.animate(piece)
    result = main()
    assert result == 123


def test_type_module(pyobj_creg, resources_root, loader):
    dir = 'type_module'
    source_text = resources_root.joinpath(dir, 'sample.types').read_text()
    resources, sources = loader({'a-project': dir})
    piece = resources['a-project', ('sample',), 'sample_record']
    t = pyobj_creg.animate(piece)
    assert isinstance(t, TRecord)
    assert sources[piece] == ('a-project', ('sample',), TextSource(source_text))


def test_type_module_resolve_local(pyobj_creg, resources_root, loader):
    dir = 'type_module_resolve_local'
    source_text = resources_root.joinpath(dir, 'sample.types').read_text()
    resources, sources = loader({'a-project': dir})
    outer_mt = resources['a-project', ('sample',), 'outer_record']
    outer_t = pyobj_creg.animate(outer_mt)
    inner_t = outer_t.fields['inner']
    inner_mt = pyobj_creg.actor_to_piece(inner_t)
    assert isinstance(outer_t, TRecord)
    assert isinstance(inner_t, TRecord)
    assert sources[outer_mt] == ('a-project', ('sample',), TextSource(source_text))
    assert sources[inner_mt] == ('a-project', ('sample',), TextSource(source_text))


def test_type_module_resolve_imports(pyobj_creg, resources_root, loader):
    dir = 'type_module_resolve_imports'
    source_1_text = resources_root.joinpath(dir, 'sample_1.types').read_text()
    source_2_text = resources_root.joinpath(dir, 'sample_2.types').read_text()
    source_3_text = resources_root.joinpath(dir, 'sample_3.types').read_text()
    resources, sources = loader({'a-project': dir})
    outer_mt = resources['a-project', ('sample_3',), 'outer_record']
    outer_t = pyobj_creg.animate(outer_mt)
    middle_t = outer_t.fields['middle']
    middle_mt = pyobj_creg.actor_to_piece(middle_t)
    inner_t = middle_t.fields['inner']
    inner_mt = pyobj_creg.actor_to_piece(inner_t)
    assert isinstance(outer_t, TRecord)
    assert isinstance(middle_t, TRecord)
    assert isinstance(inner_t, TRecord)
    assert inner_mt == resources['a-project', ('sample_1',), 'inner_record']
    assert sources[inner_mt] == ('a-project', ('sample_1',), TextSource(source_1_text))
    assert sources[middle_mt] == ('a-project', ('sample_2',), TextSource(source_2_text))
    assert sources[outer_mt] == ('a-project', ('sample_3',), TextSource(source_3_text))


def test_type_module_resolve_builtin_type(pyobj_creg, resources_root, loader):
    dir = 'type_module_resolve_builtin_type'
    source_text = resources_root.joinpath(dir, 'sample.types').read_text()
    resources, sources = loader({'a-project': dir})
    piece = resources['a-project', ('sample',), 'sample_record']
    t = pyobj_creg.animate(piece)
    assert isinstance(t, TRecord)
    assert t.fields['an_int'] is tInt
    assert t.fields['a_string'] is tString
    assert sources[piece] == ('a-project', ('sample',), TextSource(source_text))
