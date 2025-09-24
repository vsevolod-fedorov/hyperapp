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
def derived_t():
    return htypes.bundler_tests.derived


@mark.fixture.obj
def complex_t():
    return htypes.bundler_tests.complex


@mark.fixture.obj
def too_complex_t():
    return htypes.bundler_tests.too_complex


@mark.fixture.obj
def composite_t():
    return htypes.bundler_tests.composite


@mark.fixture.obj
def simple_mt(simple_t):
    return pyobj_creg.actor_to_piece(simple_t)


@mark.fixture.obj
def derived_mt(derived_t):
    return pyobj_creg.actor_to_piece(derived_t)


@mark.fixture.obj
def complex_mt(complex_t):
    return pyobj_creg.actor_to_piece(complex_t)


@mark.fixture.obj
def too_complex_mt(too_complex_t):
    return pyobj_creg.actor_to_piece(too_complex_t)


@mark.fixture.obj
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


def test_base_type_should_be_before_derived_type(bundler, index, derived_t, simple_mt, derived_mt):
    derived = derived_t(id=123, value='sample value')
    rb = bundler([mosaic.put(derived)])
    assert index(rb.bundle, simple_mt) < index(rb.bundle, derived_mt)


def test_field_type_should_be_before_complex_type(bundler, index, simple_t, complex_t, simple_mt, complex_mt):
    complex = complex_t(
        inner=simple_t(id=123),
        )
    rb = bundler([mosaic.put(complex)])
    assert index(rb.bundle, simple_mt) < index(rb.bundle, complex_mt) < index(rb.bundle, complex)


def test_both_field_types_should_be_before_complex_type(
        bundler, index, simple_t, derived_t, too_complex_t, simple_mt, derived_mt, too_complex_mt):
    too_complex = too_complex_t(
        simple=simple_t(id=111),
        derived=derived_t(id=222, value='sample value'),
        )
    rb = bundler([mosaic.put(too_complex)])
    assert (index(rb.bundle, simple_mt)
            < index(rb.bundle, derived_mt)
            < index(rb.bundle, too_complex_mt)
            < index(rb.bundle, too_complex)
            )
