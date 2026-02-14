import weakref

from . import htypes
from .services import (
    pyobj_creg,
    )
from .code.mark import mark
from .code.context import Context
from .tested.code import system_fn


def _sample_fn(view, sample_service):
    return f'sample-fn: {view}, {sample_service}'


@mark.fixture.obj
def sample_service():
    return 'a-service'


@mark.fixture.obj
def view():
    return 'a-view'


@mark.fixture.obj
def piece():
    return htypes.system_fn.ctx_fn(
        function=pyobj_creg.actor_to_ref(_sample_fn),
        ctx_params=('view',),
        service_params=('sample_service',),
        )


def test_construct(system_fn_creg, piece):
    fn = system_fn_creg.animate(piece)
    assert isinstance(fn, system_fn.ContextFn)
    assert fn.piece == piece


def test_call(system_fn_creg, view, piece):
    ctx = Context(
        view=view,
        )
    fn = system_fn_creg.animate(piece)
    result = fn(ctx)
    assert result == 'sample-fn: a-view, a-service', repr(result)
