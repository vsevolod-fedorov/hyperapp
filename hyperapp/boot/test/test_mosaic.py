import pytest

from hyperapp.boot.htypes.meta_type import add_types_to_pyobj_creg_cache, register_builtin_mt
from hyperapp.boot import cdr_coders  # register codec


pytest_plugins = [
    'hyperapp.boot.test.services',
    ]


@pytest.fixture
def init(mosaic, web, pyobj_creg, builtin_name_to_type):
    pyobj_creg.init(mosaic, web)
    add_types_to_pyobj_creg_cache(pyobj_creg, builtin_name_to_type)
    register_builtin_mt(mosaic, pyobj_creg)


def test_string(mosaic, web, init):
    value = "Sample string"
    ref = mosaic.put(value)  # Cached now.
    result_value = web.summon(ref)
    assert result_value == value


def test_bool_does_not_replace_int(mosaic, web, init):
    _ = mosaic.put(True)  # Cached now.
    ref = mosaic.put(1)  # Should not pick previously cached bool.
    value = web.summon(ref)
    assert type(value) is int
