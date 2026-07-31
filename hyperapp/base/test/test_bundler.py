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


def test_empty_record_type_index(htypes, pyobj_creg, mosaic, bundler):
    value = htypes.empty_record()
    value_ref = mosaic.put(value)
    type_ref = pyobj_creg.actor_to_ref(htypes.empty_record)
    refs_and_bundle = bundler.bundle([value_ref])
    assert refs_and_bundle.bundle
    refs = [make_ref(capsule) for capsule in refs_and_bundle.bundle.capsule_list]
    assert refs.index(type_ref) < refs.index(value_ref)
