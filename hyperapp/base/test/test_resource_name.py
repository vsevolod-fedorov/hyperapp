from pathlib import Path

import pytest

from hyperapp.boot.htypes.attribute import attribute_t
from hyperapp.boot.htypes.python_module import import_rec_t, imports_t, python_module_t
from hyperapp.boot.boot import boot
from hyperapp.boot.config_key_error import ConfigKeyError

TEST_DIR = Path(__file__).parent.resolve()


@pytest.fixture
def module():
    return boot(TEST_DIR / 'projects.yaml', 'test:boot:boot.module')


@pytest.fixture
def mosaic(module):
    return module.mosaic


@pytest.fixture
def name_resources(module):
    return module.make_name_resources()


def _python_module(mosaic, name, imports=()):
    return python_module_t(
        module_name=name,
        source=f'# {name}\n',
        imports=imports_t(
            pyobj=tuple(import_rec_t(full_name, mosaic.put(piece)) for full_name, piece in imports),
            raw=(),
            ),
        )


def test_located_module(mosaic, name_resources):
    module = _python_module(mosaic, 'module_1')
    piece_to_name = name_resources({}, {('proj', ('dir', 'module_1')): module})
    assert piece_to_name == {module: ('proj', ('dir', 'module_1'), 'module_1.module')}


def test_located_module_replaces_known_name(mosaic, name_resources):
    module = _python_module(mosaic, 'module_1')
    known_names = {('proj', ('old',), 'old.module'): module}
    piece_to_name = name_resources(known_names, {('proj', ('module_1',)): module})
    assert piece_to_name == {module: ('proj', ('module_1',), 'module_1.module')}


def test_elements(mosaic, name_resources):
    known_module = _python_module(mosaic, 'known')
    other_module = _python_module(mosaic, 'other')
    cls = attribute_t(object=mosaic.put(other_module), attr_name='SomeClass')
    method = attribute_t(object=mosaic.put(cls), attr_name='some_method')
    module = _python_module(mosaic, 'module_1', imports=[
        ('code.known', known_module),
        ('code.other.some_method', method),
        ])
    known_names = {('base', ('known',), 'known.module'): known_module}
    piece_to_name = name_resources(known_names, {('proj', ('module_1',)): module})
    location = ('proj', ('module_1',))
    assert piece_to_name == {
        module: (*location, 'module_1.module'),
        other_module: (*location, 'other.module'),
        cls: (*location, 'other.SomeClass.attr'),
        method: (*location, 'other.SomeClass.some_method.attr'),
        }


def test_element_of_other_location(mosaic, name_resources):
    module_1 = _python_module(mosaic, 'module_1')
    module_2 = _python_module(mosaic, 'module_2', imports=[('code.module_1', module_1)])
    # Referring module goes first, element still gets its own location.
    resource_locations = {
        ('proj', ('module_2',)): module_2,
        ('proj', ('module_1',)): module_1,
        }
    piece_to_name = name_resources({}, resource_locations)
    assert piece_to_name == {
        module_1: ('proj', ('module_1',), 'module_1.module'),
        module_2: ('proj', ('module_2',), 'module_2.module'),
        }


def test_name_clash(mosaic, name_resources):
    module_1 = _python_module(mosaic, 'same')
    module_2 = python_module_t(module_name='same', source='# Other\n', imports=imports_t(pyobj=(), raw=()))
    module = _python_module(mosaic, 'module', imports=[('code.a', module_1), ('code.b', module_2)])
    with pytest.raises(RuntimeError) as excinfo:
        name_resources({}, {('proj', ('module',)): module})
    assert 'proj:module:same.module is derived for two pieces' in str(excinfo.value)


def test_unknown_type(mosaic, name_resources):
    with pytest.raises(ConfigKeyError):
        name_resources({}, {('proj', ('module',)): import_rec_t('code.x', mosaic.put('x'))})
