import logging

import pytest

from hyperapp.boot.htypes.python_module import python_module_t
from hyperapp.boot.resource.source import ResourceModuleSource, TextSource

log = logging.getLogger(__name__)


pytest_plugins = [
    'hyperapp.boot.test.services',
    'hyperapp.boot.resource.test.services',
    'hyperapp.boot.resource.test.loader',
    ]


@pytest.fixture
def resources_dir(test_dir):
    return test_dir / 'resources' / 'python_module'


def test_module(pyobj_creg, loader):
    resources, sources = loader({'a-project': 'module'})
    piece = resources['a-project', ('sample',), 'a_module.module']
    assert isinstance(piece, python_module_t)
    assert "Hello from" in piece.source
    module = pyobj_creg.animate(piece)
    assert module.a_value == 12345
    assert sources[piece.source] == ('a-project', ('a_module.dyn.py',), TextSource(piece.source))
    assert sources[piece] == ('a-project', ('sample',), ResourceModuleSource('a_module.module'))


def test_fn(pyobj_creg, loader):
    resources, sources = loader({'a-project': 'fn'})
    piece = resources['a-project', ('sample',), 'fn']
    fn = pyobj_creg.animate(piece)
    result = fn()
    assert result == 123


def test_code_import(pyobj_creg, loader):
    resources, sources = loader({'a-project': 'code_import'})
    piece = resources['a-project', ('sample',), 'main']
    main = pyobj_creg.animate(piece)
    result = main()
    assert result == 123


def test_code_and_htypes_import(pyobj_creg, loader):
    resources, sources = loader({'a-project': 'import'})
    piece = resources['a-project', ('sample',), 'main']
    main = pyobj_creg.animate(piece)
    result = main()
    assert result == 123


def test_package_import(pyobj_creg, loader):
    resources, sources = loader({'a-project': 'package_import'})
    piece = resources['a-project', ('sample',), 'main']
    main = pyobj_creg.animate(piece)
    assert main() == 100


def test_builtin_services(pyobj_creg, loader):
    resources, sources = loader({'a-project': 'builtin_services'})
    fn_piece = resources['a-project', ('sample',), 'run_tests']
    run_tests = pyobj_creg.animate(fn_piece)
    result = run_tests()
    assert result == 'ok'
