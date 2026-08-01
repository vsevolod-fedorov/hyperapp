from pathlib import Path

import pytest

from hyperapp.boot.ref import make_ref
from hyperapp.boot.boot import boot

TEST_DIR = Path(__file__).parent.resolve()


@pytest.fixture
def module():
    return boot(TEST_DIR / 'projects.yaml', 'test:boot:boot.module')


@pytest.fixture
def htypes(module):
    return module.htypes.test


@pytest.fixture
def pyobj_creg(module):
    return module.pyobj_creg


@pytest.fixture
def mosaic(module):
    return module.mosaic


@pytest.fixture
def bundler(module):
    return module.make_bundler()


@pytest.fixture
def unbundler(module):
    return module.unbundler


@pytest.fixture
def bundle(bundler, unbundler):
    saved = []
    def _bundle(ref):
        refs_and_bundle = bundler.bundle([ref])
        saved.append(refs_and_bundle.bundle)
        return [make_ref(capsule) for capsule in refs_and_bundle.bundle.capsule_list]
    yield _bundle
    # Check it could be unbundled
    unbundler.register_bundle(saved[0])


def test_type_should_be_before_value(htypes, pyobj_creg, mosaic, bundle):
    t = htypes.empty
    value_ref = mosaic.put(t())
    type_ref = pyobj_creg.actor_to_ref(t)
    refs = bundle(value_ref)
    assert refs.index(type_ref) < refs.index(value_ref)


def test_type_should_be_before_both_values(htypes, pyobj_creg, mosaic, bundle):
    element_t = htypes.simple
    list_t = htypes.ref_list
    values = (
        mosaic.put(element_t(100)),
        mosaic.put(element_t(200)),
        )
    container_ref = mosaic.put(list_t(values))
    element_t_ref = pyobj_creg.actor_to_ref(element_t)
    list_t_ref = pyobj_creg.actor_to_ref(list_t)
    refs = bundle(container_ref)
    assert refs.index(list_t_ref) < refs.index(values[0])
    assert refs.index(list_t_ref) < refs.index(values[1])
    assert refs.index(element_t_ref) < refs.index(values[0])
    assert refs.index(element_t_ref) < refs.index(values[1])
