from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.mark import mark
from .code.system_fn import ContextFn
from .tested.code import typed_cfg_item


@mark.fixture.obj
def value():
    return htypes.typed_cfg_item_tests.value()


@mark.fixture.obj
def piece(value):
    return htypes.cfg_item.typed_cfg_item(
        t=pyobj_creg.actor_to_ref(htypes.typed_cfg_item_tests.key),
        value=mosaic.put(value),
        )


def test_resolve(system, value, piece):
    resolved_value = typed_cfg_item.resolve_typed_cfg_value(piece, '<unused-key>', system, '<unused-service-name>')
    assert resolved_value == value


def _sample_fn(view, state, sample_service):
    return f'sample-fn: {state}, {sample_service}'


@mark.fixture
def sample_service():
    return 'a-service'


@mark.fixture.obj
def fn_piece():
    fn = htypes.system_fn.ctx_fn(
        function=pyobj_creg.actor_to_ref(_sample_fn),
        ctx_params=('view', 'state'),
        service_params=('sample_service',),
        )
    return htypes.cfg_item.typed_fn_cfg_item(
        t=pyobj_creg.actor_to_ref(htypes.typed_cfg_item_tests.key),
        system_fn=mosaic.put(fn),
        )


def test_fn_resolve(system, fn_piece):
    fn = typed_cfg_item.resolve_typed_fn_cfg_value(fn_piece, '<unused-key>', system, '<unused-service-name>')
    assert isinstance(fn, ContextFn)
