import logging
import weakref
from unittest.mock import AsyncMock, MagicMock, Mock

from hyperapp.boot.config_key_error import ConfigKeyError

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.context import Context
from .code.system_fn import ContextFn
from .code.model_command import ModelCommandFn
from .code.selector import Selector
from .fixtures import qapp_fixtures
from .fixtures import error_view_fixtures
from .fixtures import feed_fixtures
from .fixtures import visualizer_fixtures
from .tested.code import crud

log = logging.getLogger(__name__)


def _sample_crud_get(piece, id):
    assert isinstance(piece, htypes.crud_tests.sample_model), piece
    if id == 11:
        return htypes.crud_tests.sample_record(id, f'item#{id}')
    if id == 22:
        return htypes.crud_tests.sample_selector()
    assert id == 33
    return "Default string value"


def _sample_crud_update(piece, id, value):
    assert isinstance(piece, htypes.crud_tests.sample_model), piece
    if id == 11:
        assert isinstance(value, htypes.crud_tests.sample_record), value
        return (None, 11)
    elif id == 22:
        assert isinstance(value, htypes.crud_tests.sample_selector), value
    elif id == 33:
        assert type(value) is str, value
    else:
        assert 0, id
    log.info("Update %s: #%d -> %s", piece, id, value)


@mark.fixture
def _sample_crud_get_fn():
    return htypes.system_fn.ctx_fn(
        function=pyobj_creg.actor_to_ref(_sample_crud_get),
        ctx_params=('piece', 'id'),
        service_params=(),
        )


@mark.fixture
def _sample_crud_update_fn():
    return htypes.command.model_command_fn(
        function=pyobj_creg.actor_to_ref(_sample_crud_update),
        ctx_params=('piece', 'id', 'value'),
        service_params=(),
        )


def _sample_selector_get(value):
    assert isinstance(value, htypes.crud_tests.sample_selector), value
    return htypes.crud_tests.sample_selector_model()


def _sample_selector_pick(piece, current_item):
    assert isinstance(piece, htypes.crud_tests.sample_selector_model), piece
    assert isinstance(current_item, htypes.crud_tests.sample_selector_item)
    return htypes.crud_tests.sample_selector()


@mark.fixture
def _sample_selector_get_fn(rpc_system_call_factory):
    return ModelCommandFn(
        rpc_system_call_factory=rpc_system_call_factory,
        ctx_params=('value',),
        service_params=(),
        raw_fn=_sample_selector_get,
        )


@mark.fixture
def _sample_selector_pick_fn(rpc_system_call_factory):
    return ContextFn(
        rpc_system_call_factory=rpc_system_call_factory,
        ctx_params=('piece', 'current_item'),
        service_params=(),
        raw_fn=_sample_selector_pick,
        )


@mark.fixture
def lcs():
    lcs = Mock()
    lcs.get.return_value = None  # Used by visualizer.
    return lcs


@mark.fixture
def navigator_widget():
    return Mock()


@mark.fixture
def navigator_rec(navigator_widget):
    return Mock(view=AsyncMock(), widget_wr=weakref.ref(navigator_widget))


@mark.fixture
def ctx(generate_rsa_identity, lcs, navigator_rec):
    return Context(
        identity=generate_rsa_identity(fast=True),
        lcs=lcs,
        navigator=navigator_rec,
        )


@mark.fixture
def model():
    return htypes.crud_tests.sample_model()


@mark.fixture
def commit_command_d():
    return htypes.crud_tests.save_d()


@mark.fixture
def view_piece_ctr(generate_rsa_identity, _sample_crud_get_fn, _sample_crud_update_fn, model, commit_command_d, item_id, pick_fn):
    identity = generate_rsa_identity(fast=True)
    base_view_piece = htypes.label.view("Sample label")
    return htypes.crud.view(
        base_view=mosaic.put(base_view_piece),
        label="Sample CRUD context",
        model=mosaic.put(model),
        remote_peer=mosaic.put(identity.peer.piece),
        commit_command_d=mosaic.put(commit_command_d),
        args=(htypes.crud.arg('id', mosaic.put(item_id)),),
        pick_fn=mosaic.put_opt(pick_fn),
        commit_fn=mosaic.put(_sample_crud_update_fn),
        commit_value_field='value',
        )


@mark.fixture
def commit_command_layout_k(commit_command_d):
    return htypes.crud.layout_k(
        commit_command_d=mosaic.put(commit_command_d),
        )


@mark.fixture.obj
def model_layout_reg(format, commit_command_layout_k):
    def getitem(self, layout_k):
        def k(t):
            return htypes.ui.model_layout_k(pyobj_creg.actor_to_ref(t))
        if layout_k == k(htypes.crud_tests.sample_model):
            return htypes.label.view("Sample label")
        if layout_k == k(htypes.crud_tests.sample_selector_model):
            return htypes.crud_tests.selector_view()
        raise ConfigKeyError('model_layout_reg', layout_k)
    reg = MagicMock()
    reg.__getitem__ = getitem
    return reg


async def test_crud_context_view(view_reg, model_layout_reg, qapp, ctx, view_piece_ctr):
    piece = view_piece_ctr(11, pick_fn=None)
    view = crud.CrudContextView.from_piece(piece, ctx)
    state = None
    widget = view.construct_widget(state, ctx)
    assert view.piece == piece
    state = view.widget_state(widget)
    assert state

    # Hack: Replace base view to change layout.
    new_label = htypes.label.view("Another sample label")
    view._base_view = view_reg.animate(new_label, ctx)
    rctx = Context()
    await view.children_changed(ctx, rctx, widget, save_layout=True)
    model_layout_reg.__setitem__.assert_called_once()
    assert isinstance(model_layout_reg.__setitem__.call_args.args[0], htypes.crud.layout_k)


def test_record_adapter(_sample_crud_get_fn, ctx, model, commit_command_d):
    value_t = htypes.crud_tests.sample_record
    item_id = 11
    form_model = htypes.crud.form_model(
        model=mosaic.put(model),
        record_t=pyobj_creg.actor_to_ref(value_t),
        commit_command_d=mosaic.put(commit_command_d),
        init_fn=mosaic.put(_sample_crud_get_fn),
        args=(htypes.crud.arg('id', mosaic.put(item_id)),),
        )
    piece = htypes.crud.record_adapter()
    adapter = crud.CrudRecordAdapter.from_piece(piece, form_model, ctx)

    assert adapter.record_t == value_t
    assert adapter.get_field('id') == 11
    assert adapter.get_field('text') == "item#11"


@mark.fixture
async def run_open_command_fn_test(ctx, navigator_rec, _sample_crud_get_fn, _sample_crud_update_fn, commit_command_d, value_t, item_id):
    piece = htypes.crud.open_command_fn(
        name='edit',
        value_t=pyobj_creg.actor_to_ref(value_t),
        key_fields=('id',),
        init_action_fn=mosaic.put(_sample_crud_get_fn),
        commit_command_d=mosaic.put(commit_command_d),
        commit_action_fn=mosaic.put(_sample_crud_update_fn),
        )
    fn = crud.CrudOpenFn.from_piece(piece)
    assert fn.piece == piece

    assert fn.missing_params(Context()) == {'navigator', 'model', 'current_item'}
    ctx = ctx.clone_with(
        navigator=navigator_rec,
        model=htypes.crud_tests.sample_model(),
        current_item=htypes.crud_tests.sample_item(id=item_id),
        )
    assert not fn.missing_params(ctx)
    await fn.call(ctx)
    navigator_rec.view.open.assert_awaited_once()


async def test_open_command_fn_to_form(run_open_command_fn_test):
    value_t = htypes.crud_tests.sample_record
    await run_open_command_fn_test(value_t, item_id=11)


async def test_open_command_fn_to_str(run_open_command_fn_test):
    value_t = htypes.builtin.string
    await run_open_command_fn_test(value_t, item_id=33)


@mark.config_fixture('selector_reg')
def selector_reg_config(_sample_selector_get_fn, _sample_selector_pick_fn):
    value_t = htypes.crud_tests.sample_selector
    selector = Selector(
        model_t=htypes.crud_tests.sample_selector_model,
        get_fn=_sample_selector_get_fn,
        pick_fn=_sample_selector_pick_fn,
        )
    return {value_t: selector}


@mark.config_fixture('view_reg')
def view_reg_config(view_fn_mock, visualizer_view_reg_config):
    return {
        **visualizer_view_reg_config,
        **view_fn_mock(htypes.crud_tests.selector_view()),
        }


async def test_open_command_fn_to_selector(run_open_command_fn_test):
    value_t = htypes.crud_tests.sample_selector
    await run_open_command_fn_test(value_t, item_id=22)


@mark.fixture
def rpc_system_call_factory(receiver_peer, sender_identity, fn):
    def call(**kw):
        ctx = Context(**kw)
        return fn.call(ctx)
    return call


async def test_commit_command_enum_for_form(view_reg, ctx, view_piece_ctr, model):
    view_piece = view_piece_ctr(11, pick_fn=None)
    view = view_reg.animate(view_piece, ctx)
    commands = crud.crud_commit_command_enum(view)
    assert commands
    [unbound_cmd] = commands
    assert unbound_cmd.properties
    value = htypes.crud_tests.sample_record(12345, "Some text")
    input = Mock()
    input.get_value.return_value = value
    command_ctx = ctx.push(
        model=model,
        piece=model,
        input=input,
        )
    bound_cmd = unbound_cmd.bind(command_ctx)
    assert bound_cmd.enabled
    await bound_cmd.run()


async def test_commit_command_enum_for_selector(view_reg, ctx, _sample_selector_pick_fn, view_piece_ctr):
    view_piece = view_piece_ctr(22, pick_fn=_sample_selector_pick_fn.piece)
    view = view_reg.animate(view_piece, ctx)
    commands = crud.crud_commit_command_enum(view)
    assert commands
    [unbound_cmd] = commands
    assert unbound_cmd.properties
    model = htypes.crud_tests.sample_selector_model()
    current_item = htypes.crud_tests.sample_selector_item()
    command_ctx = ctx.clone_with(
        model=model,
        piece=model,
        current_item=current_item,
        )
    bound_cmd = unbound_cmd.bind(command_ctx)
    assert bound_cmd.enabled
    await bound_cmd.run()


def test_layout_k_resource_name(commit_command_layout_k):
    gen = Mock()
    gen.assigned_name.return_value = 'some_command'
    name = crud.layout_k_resource_name(commit_command_layout_k, gen)
    assert type(name) is str


def test_format_layout_k(commit_command_layout_k):
    title = crud.format_layout_k(commit_command_layout_k)
    assert type(title) is str
