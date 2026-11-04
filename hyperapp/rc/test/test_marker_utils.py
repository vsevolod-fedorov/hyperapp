from pathlib import Path

import pytest

from hyperapp.boot.boot import boot


TEST_DIR = Path(__file__).parent.resolve()


@pytest.fixture
def module():
    return boot(TEST_DIR / 'projects.yaml', 'rc:marker_utils:marker_utils.module')


class Wrapper:

    def __init__(self, fn):
        self._fn = fn

    @property
    def real_fn(self):
        return self._fn


def test_real_fn_unwraps_nested_wrappers(module):
    def fn():
        pass

    assert module.real_fn(Wrapper(Wrapper(fn))) is fn
    assert module.check_is_function(Wrapper(Wrapper(fn))) is fn


def test_check_is_function_rejects_other_objects(module):
    with pytest.raises(RuntimeError, match='Expected function, classmethod or staticmethod'):
        module.check_is_function(object())


def test_check_not_classmethod(module):
    def fn():
        pass

    module.check_not_classmethod(fn)
    with pytest.raises(RuntimeError, match='place the marker before the @classmethod decorator'):
        module.check_not_classmethod(classmethod(fn))
