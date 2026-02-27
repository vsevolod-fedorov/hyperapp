from unittest.mock import Mock

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.mark import mark
from .code.context import Context
from .code.selector import Selector
from .fixtures import qapp_fixtures
from .tested.code import arg_mark


@mark.fixture
def model():
    return htypes.arg_mark_tests.sample_model()


@mark.fixture
def value():
    return htypes.arg_mark_tests.sample_value()


def test_view(qapp, model, value):
    base_piece = htypes.label.view("Sample label")
    piece = htypes.arg_mark.view(
        base=mosaic.put(base_piece),
        model=mosaic.put(model),
        value=mosaic.put(value),
        )
    ctx = Context(
        piece=piece,
        )
    base_state = htypes.label.state()
    state = htypes.context_view.state(
        base=mosaic.put(base_state),
        )
    view = arg_mark.MarkView.from_piece(ctx)
    widget = view.construct_widget(state, ctx)
    assert view.piece == piece
    state = view.widget_state(widget)
    assert state
    children_ctx = view.children_context(ctx)
    assert children_ctx


@mark.fixture
def base_view(model):
    return Mock(
        piece=htypes.arg_mark_tests.sample_view(),
        model=model,
        )


@mark.config_fixture('view_reg')
def view_reg_fixture(base_view):
    return {
        htypes.arg_mark_tests.sample_view: base_view,
        }


@mark.config_fixture('selector_reg')
def selector_reg_config():
    value_t = htypes.arg_mark_tests.sample_value
    selector = Selector(
        model_t=htypes.arg_mark_tests.sample_model,
        open_action=None,
        pick_action=htypes.arg_mark_tests.sample_selector_pick_action(),
        )
    return {value_t: selector}


def pick_action(ctx):
    return htypes.arg_mark_tests.sample_value()


@mark.config_fixture('selector_pick_action_creg')
def selector_pick_action_creg_config():
    return {
        htypes.arg_mark_tests.sample_selector_pick_action: pick_action,
        }


def test_add_mark(view_reg, model, base_view):
    ctx = Context(
        model_state=htypes.arg_mark_tests.sample_model_state(),
        )
    navigator_piece = htypes.navigator.view(
        current_view=mosaic.put(base_view.piece),
        current_model=mosaic.put(model),
        layout_k=None,
        prev=None,
        next=None,
        )
    navigator = view_reg.animate(navigator_piece, ctx)
    state = htypes.arg_mark_tests.sample_state()
    hook = Mock()
    result = arg_mark.add_mark(navigator, state, hook, ctx)
    hook.replace_view.assert_called_once()
    new_view = hook.replace_view.call_args.args[0]
    assert isinstance(new_view, arg_mark.MarkView)
    assert web.summon_opt(new_view.piece.value) == htypes.arg_mark_tests.sample_value()


def test_remove_mark(view_reg, model, value):
    ctx = Context()
    label_view = htypes.label.view("Sample label")
    label_state = htypes.label.state()
    view_piece = htypes.arg_mark.view(
        base=mosaic.put(label_view),
        model=mosaic.put(model),
        value=mosaic.put(value),
        )
    state = htypes.context_view.state(
        base=mosaic.put(label_state),
        )
    view = view_reg.animate(view_piece, ctx)
    hook = Mock()
    result = arg_mark.remove_mark(view, state, hook, ctx)
    hook.replace_view.assert_called_once()
