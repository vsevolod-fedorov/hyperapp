from hyperapp.boot.ref import decode_capsule

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .tested.code import bundler


@mark.fixture.obj
def simple_t():
    return htypes.bundler_tests.simple


@mark.fixture.obj
def composite_t():
    return htypes.bundler_tests.composite


@mark.fixture
def simple_mt(simple_t):
    return pyobj_creg.actor_to_piece(simple_t)


@mark.fixture
def composite_mt(composite_t):
    return pyobj_creg.actor_to_piece(composite_t)


@mark.fixture
def index(bundle, value):
    dcl = [decode_capsule(pyobj_creg, capsule) for capsule in bundle.capsule_list]
    return next(idx for idx, dc in enumerate(dcl) if dc.value == value)


def test_type_should_be_before_value(bundler, index, simple_t, simple_mt):
    simple = simple_t(id=123)
    rb = bundler([mosaic.put(simple)])
    assert len(rb.bundle.roots) == 1
    assert web.summon(rb.bundle.roots[0]) == simple
    assert index(rb.bundle, simple_mt) < index(rb.bundle, simple)


def test_type_should_be_before_both_values(bundler, simple_t, composite_t, simple_mt, composite_mt):
    simple_1 = simple_t(id=111)
    simple_2 = simple_t(id=222)
    composite = composite_t(
        elements=(
            mosaic.put(simple_1),
            mosaic.put(simple_2),
            ),
        )
    rb = bundler([mosaic.put(composite)])
    assert index(rb.bundle, simple_mt) < index(rb.bundle, simple_1)
    assert index(rb.bundle, simple_mt) < index(rb.bundle, simple_2)


def test_type_should_be_before_type_it_is_used_in(bundler, index, simple_t, composite_t, simple_mt, composite_mt):
    simple = simple_t(id=123)
    composite = composite_t(
        elements=(mosaic.put(simple),),
        )
    rb = bundler([mosaic.put(composite)])
    assert index(rb.bundle, simple_mt) < index(rb.bundle, composite_mt) < index(rb.bundle, composite)
