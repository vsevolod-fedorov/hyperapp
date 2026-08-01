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
def bundle(mosaic, bundler, unbundler):
    saved = []
    def _bundle(piece):
        refs_and_bundle = bundler.bundle([mosaic.put(piece)])
        saved.append(refs_and_bundle.bundle)
        return [
            mosaic.resolve_ref(make_ref(capsule)).value
            for capsule in refs_and_bundle.bundle.capsule_list
            ]
    yield _bundle
    # Check it could be unbundled
    if saved:
        unbundler.register_bundle(saved[0])


def test_type_should_be_before_value(htypes, pyobj_creg, mosaic, bundle):
    t = htypes.empty
    value = t()
    type_mt = pyobj_creg.actor_to_piece(t)
    pieces = bundle(value)
    assert pieces.index(type_mt) < pieces.index(value)


def test_type_should_be_before_both_values(htypes, pyobj_creg, mosaic, bundle):
    element_t = htypes.simple
    list_t = htypes.ref_list
    elements = [
        element_t(100),
        element_t(200),
        ]
    container = list_t(tuple(mosaic.put(e) for e in elements))
    element_mt = pyobj_creg.actor_to_piece(element_t)
    list_mt = pyobj_creg.actor_to_piece(list_t)
    pieces = bundle(container)
    assert pieces.index(list_mt) < pieces.index(elements[0])
    assert pieces.index(list_mt) < pieces.index(elements[1])
    assert pieces.index(element_mt) < pieces.index(elements[0])
    assert pieces.index(element_mt) < pieces.index(elements[1])


def test_base_type_should_be_before_derived_type(htypes, pyobj_creg, mosaic, bundle):
    value = htypes.derived(id=123, value='sample value')
    simple_mt = pyobj_creg.actor_to_piece(htypes.simple)
    derived_mt = pyobj_creg.actor_to_piece(htypes.derived)
    pieces = bundle(value)
    assert pieces.index(simple_mt) < pieces.index(derived_mt)
    assert pieces.index(derived_mt) < pieces.index(value)
