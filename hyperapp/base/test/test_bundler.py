from collections import Counter
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
def assoc_pickers():
    return []


@pytest.fixture
def bundler(module, assoc_pickers):
    return module.make_bundler(assoc_pickers)


@pytest.fixture
def unbundler(module):
    return module.unbundler


@pytest.fixture
def bundle(mosaic, bundler, unbundler):
    saved = []
    def _bundle(piece, size_limit=None):
        refs_and_bundle = bundler(mosaic.put(piece), size_limit=size_limit)
        saved.append(refs_and_bundle.bundle)
        pieces = [
            mosaic.resolve_ref(make_ref(capsule)).value
            for capsule in refs_and_bundle.bundle.capsule_list
            ]
        assoc_list = [
            mosaic.resolve_ref(ref).value
            for ref in refs_and_bundle.bundle.associations
            ]
        dups = [item for item, count in Counter(pieces).items() if count > 1]
        assert not dups
        assoc_dups = [item for item, count in Counter(assoc_list).items() if count > 1]
        assert not assoc_dups
        return (pieces, assoc_list)
    yield _bundle
    # Check it could be unbundled
    if saved:
        unbundler.register_bundle(saved[0])


def test_type_should_be_before_value(htypes, pyobj_creg, mosaic, bundle):
    value = htypes.empty()
    type_mt = pyobj_creg.actor_to_piece(htypes.empty)
    pieces, _ = bundle(value)
    assert value in pieces
    assert pieces.index(type_mt) < pieces.index(value)


def test_two_types(htypes, pyobj_creg, mosaic, bundle):
    empty = htypes.empty()
    simple = htypes.simple(123)
    empty_mt = pyobj_creg.actor_to_piece(htypes.empty)
    simple_mt = pyobj_creg.actor_to_piece(htypes.simple)
    container = htypes.ref_list(
        elements=(
            mosaic.put(empty),
            mosaic.put(simple),
            ),
        )
    ref_list_mt = pyobj_creg.actor_to_piece(htypes.ref_list)
    pieces, _ = bundle(container)
    assert pieces.index(ref_list_mt) < pieces.index(container)
    assert pieces.index(empty_mt) < pieces.index(empty)
    assert pieces.index(simple_mt) < pieces.index(simple)


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
    pieces, _ = bundle(container)
    assert pieces.index(list_mt) < pieces.index(elements[0])
    assert pieces.index(list_mt) < pieces.index(elements[1])
    assert pieces.index(element_mt) < pieces.index(elements[0])
    assert pieces.index(element_mt) < pieces.index(elements[1])


def test_base_type_should_be_before_value(htypes, pyobj_creg, mosaic, bundle):
    value = htypes.derived(id=123, value='sample value')
    simple_mt = pyobj_creg.actor_to_piece(htypes.simple)
    derived_mt = pyobj_creg.actor_to_piece(htypes.derived)
    pieces, _ = bundle(value)
    assert pieces.index(derived_mt) < pieces.index(value)
    assert pieces.index(simple_mt) < pieces.index(value)


def test_field_type_should_be_before_value(htypes, pyobj_creg, mosaic, bundle):
    element = htypes.simple(id=123)
    container = htypes.complex_1(
        inner=element,
        )
    simple_mt = pyobj_creg.actor_to_piece(htypes.simple)
    complex_1_mt = pyobj_creg.actor_to_piece(htypes.complex_1)
    pieces, _ = bundle(container)
    assert pieces.index(complex_1_mt) < pieces.index(container)
    assert pieces.index(simple_mt) < pieces.index(container)


def test_both_field_types_should_be_before_value(htypes, pyobj_creg, mosaic, bundle):
    container = htypes.complex_2(
        simple=htypes.simple(id=111),
        derived=htypes.derived(id=222, value='sample value'),
        )
    simple_mt = pyobj_creg.actor_to_piece(htypes.simple)
    derived_mt = pyobj_creg.actor_to_piece(htypes.derived)
    complex_2_mt = pyobj_creg.actor_to_piece(htypes.complex_2)
    pieces, _ = bundle(container)
    assert pieces.index(complex_2_mt) < pieces.index(container)
    assert pieces.index(simple_mt) < pieces.index(container)
    assert pieces.index(derived_mt) < pieces.index(container)


def test_element_type_should_be_before_value(htypes, pyobj_creg, mosaic, bundle):
    rec_list = htypes.rec_list(
        elements=(
            htypes.simple(100),
            htypes.simple(200),
            ),
        )
    simple_mt = pyobj_creg.actor_to_piece(htypes.simple)
    rec_list_mt = pyobj_creg.actor_to_piece(htypes.rec_list)
    pieces, _ = bundle(rec_list)
    assert pieces.index(rec_list_mt) < pieces.index(rec_list)
    assert pieces.index(simple_mt) < pieces.index(rec_list)


def test_size_limit(htypes, pyobj_creg, mosaic, bundle):
    small = htypes.simple(id=123)
    big = htypes.big(value='x' * 102400)
    container = htypes.ref_list(
        elements=(
            mosaic.put(small),
            mosaic.put(big),
            ),
        )
    simple_mt = pyobj_creg.actor_to_piece(htypes.simple)
    big_mt = pyobj_creg.actor_to_piece(htypes.big)
    ref_list_mt = pyobj_creg.actor_to_piece(htypes.ref_list)
    pieces, _ = bundle(container, size_limit=10240)
    assert container in pieces
    assert small in pieces
    assert pieces.index(simple_mt) < pieces.index(small)
    assert pieces.index(ref_list_mt) < pieces.index(container)
    assert big not in pieces
    assert big_mt not in pieces


def test_association_included(htypes, pyobj_creg, mosaic, assoc_pickers, bundle):
    value = htypes.simple(id=1)
    assoc = htypes.simple(id=2)

    def picker(v):
        if v == value:
            return [assoc]

    assoc_pickers.append(picker)
    pieces, assoc_list = bundle(value)
    assert value in pieces
    assert assoc in pieces
    assert assoc_list == [assoc]


def test_association_refs_included(htypes, pyobj_creg, mosaic, assoc_pickers, bundle):
    value = htypes.simple(id=1)
    element = htypes.simple(id=2)
    assoc = htypes.ref_list(
        elements=(
            mosaic.put(element),
            ),
        )

    def picker(v):
        if v == value:
            return [assoc]

    assoc_pickers.append(picker)
    pieces, assoc_list = bundle(value)
    assert value in pieces
    assert assoc in pieces
    assert assoc_list == [assoc]
    assert element in pieces


def test_big_association_should_prevent_value_from_be_included(
        htypes, pyobj_creg, mosaic, assoc_pickers, bundle):
    first = htypes.simple(id=1)
    second = htypes.simple(id=2)
    small_assoc = htypes.big(value='x')
    big_assoc = htypes.big(value='x' * 102400)
    container = htypes.ref_list(
        elements=(
            mosaic.put(first),
            mosaic.put(second),
            ),
        )

    def picker(v):
        if v == first:
            return [small_assoc]
        if v == second:
            return [big_assoc]

    assoc_pickers.append(picker)
    pieces, assoc_list = bundle(container, size_limit=10240)
    assert first in pieces
    assert assoc_list == [small_assoc]
    assert small_assoc in pieces
    assert big_assoc not in pieces
    assert second not in pieces
