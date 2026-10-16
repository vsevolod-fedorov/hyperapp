from pathlib import Path
from types import SimpleNamespace

import pytest

from hyperapp.boot.htypes.python_module import import_rec_t, imports_t, python_module_t
from hyperapp.boot.boot import boot

TEST_DIR = Path(__file__).parent.resolve()


@pytest.fixture
def module():
    return boot(TEST_DIR / 'projects.yaml', 'test:boot:boot.module')


@pytest.fixture
def mosaic(module):
    return module.mosaic


@pytest.fixture
def pyobj_creg(module):
    return module.pyobj_creg


@pytest.fixture
def dump_resource_modules(module):
    return module.resource_dump.dump_resource_modules


def _python_module(mosaic, name, imports=()):
    return python_module_t(
        module_name=name,
        source=f'# {name}\n',
        imports=imports_t(
            pyobj=tuple(import_rec_t(full_name, mosaic.put(piece)) for full_name, piece in imports),
            raw=(),
            ),
        )


def test_refs(mosaic, pyobj_creg, dump_resource_modules):
    sibling = _python_module(mosaic, 'sibling')
    nested = _python_module(mosaic, 'nested')
    other_dir = _python_module(mosaic, 'other_dir')
    other_project = _python_module(mosaic, 'other_project')
    module = _python_module(mosaic, 'module_1', imports=[
        ('code.nested', nested),
        ('code.other_dir', other_dir),
        ('code.other_project', other_project),
        ('code.sibling', sibling),
        ])
    location = ('proj', ('dir', 'module_1'))
    piece_to_name = {
        pyobj_creg.actor_to_piece(python_module_t): ('builtin', ('type',), 'python_module'),
        module: (*location, 'module_1.module'),
        sibling: ('proj', ('dir', 'sibling'), 'sibling.module'),
        nested: ('proj', ('dir', 'sub', 'nested'), 'nested.module'),
        other_dir: ('proj', ('other', 'other_dir'), 'other_dir.module'),
        other_project: ('base_project', ('lib',), 'other_project.module'),
        }
    projects = {
        'proj': SimpleNamespace(imports={'base': 'base_project'}),
        }
    location_to_text = dump_resource_modules(projects, piece_to_name, {location})
    expected_path = TEST_DIR / 'resource_dump.resources.expected.yaml'
    assert location_to_text == {location: expected_path.read_text()}


def test_not_imported_project(mosaic, pyobj_creg, dump_resource_modules):
    other_project = _python_module(mosaic, 'other_project')
    module = _python_module(mosaic, 'module_1', imports=[('code.other_project', other_project)])
    location = ('proj', ('module_1',))
    piece_to_name = {
        pyobj_creg.actor_to_piece(python_module_t): ('builtin', ('type',), 'python_module'),
        module: (*location, 'module_1.module'),
        other_project: ('base_project', ('lib',), 'other_project.module'),
        }
    projects = {
        'proj': SimpleNamespace(imports={}),
        }
    with pytest.raises(RuntimeError) as excinfo:
        dump_resource_modules(projects, piece_to_name, {location})
    assert "Project 'base_project' is not imported" in str(excinfo.value)
