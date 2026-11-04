from pathlib import Path

import pytest

from hyperapp.boot.boot import boot
from hyperapp.boot.htypes import TRecord


TEST_DIR = Path(__file__).parent.resolve()


@pytest.fixture
def module():
    return boot(TEST_DIR / 'projects.yaml', 'base:mark:mark.module')


def test_bare_decoration_is_noop(module):
    @module.mark.some.nested.marker
    def fn():
        return 'result'

    assert fn() == 'result'


def test_parameterized_decoration_is_noop(module):
    @module.mark.some.nested.marker()
    def undecorated():
        return 'plain'

    @module.mark.some.nested.marker(1, 'two', option=3)
    def parameterized():
        return 'params'

    assert undecorated() == 'plain'
    assert parameterized() == 'params'


def test_string_and_type_parameters_are_noop_decorators(module):
    marker_type = TRecord('test_mark', 'marker_param', {})

    @module.mark.marker('service')
    def string_parameterized():
        pass

    @module.mark.marker(marker_type)
    def type_parameterized():
        pass

    assert callable(string_parameterized)
    assert callable(type_parameterized)


def test_noop_returns_original_callable(module):
    def fn():
        pass

    assert module.mark.marker(fn) is fn
    assert module.mark.marker()(fn) is fn
    assert module.mark.marker('param')(fn) is fn
    assert module.mark.marker(1)(fn) is fn


def test_activation_is_cleaned_up(module):
    class Registry:

        def __init__(self):
            self.providers = []

        def make_marker(self, marker_path, provider_path):
            self.providers.append((marker_path, provider_path))
            return lambda fn: fn

    registry = Registry()

    def fn():
        pass

    with module.markers_activated(registry, {__name__: 'sample:first'}):
        assert module.mark.active(fn) is fn
    assert registry.providers == [(('active',), 'sample:first')]
    assert module.mark.active(fn) is fn
    assert len(registry.providers) == 1

    with pytest.raises(RuntimeError, match='job failed'):
        with module.markers_activated(registry, {__name__: 'sample:failed'}):
            raise RuntimeError('job failed')
    assert module.mark.active(fn) is fn
    assert len(registry.providers) == 1

    with module.markers_activated(registry, {__name__: 'sample:next'}):
        assert module.mark.active(fn) is fn
    assert registry.providers[-1] == (('active',), 'sample:next')
