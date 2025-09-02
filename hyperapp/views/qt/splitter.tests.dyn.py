from unittest.mock import Mock

from . import htypes
from .services import (
    deduce_t,
    mosaic,
    pyobj_creg,
    )
from .code.mark import mark
from .code.context import Context
from .fixtures import qapp_fixtures
from .tested.code import splitter


@mark.fixture
def piece():
    label_1 = htypes.label.view("Sample label 1")
    label_2 = htypes.label.view("Sample label 2")
    return htypes.splitter.view(
        orientation='Horizontal',
        elements=[
            mosaic.put(label_1),
            mosaic.put(label_2),
            ],
        )


@mark.fixture
def state():
    label_state = htypes.label.state()
    return htypes.splitter.state(
        current=0,
        elements=[
            mosaic.put(label_state),
            mosaic.put(label_state),
            ],
        )


@mark.fixture
def ctx():
    return Context()


def test_view(qapp, piece, state, ctx):
    view = splitter.SplitterView.from_piece(piece, ctx)
    widget = view.construct_widget(state, ctx)
    assert view.piece
    state = view.widget_state(widget)
    assert state


def test_unwrap(qapp, piece, state, ctx, view_reg):
    view = view_reg.animate(piece, ctx)
    hook = Mock()
    splitter.unwrap(view, state, hook, ctx)
    hook.replace_view.assert_called_once()


@mark.config_fixture('model_layout_reg')
def model_layout_reg_config():
    def k(t):
        return htypes.ui.model_layout_k(pyobj_creg.actor_to_ref(t))
    return {
        k(htypes.builtin.string): htypes.text.edit_view(
            adapter=mosaic.put(htypes.str_adapter.static_str_adapter()),
            ),
        }


async def test_split_horizontally(visualizer, view_reg, ctx):
    text = "Sample text"
    text_view = await visualizer(deduce_t(text))
    navigator_piece = htypes.navigator.view(
        current_view=mosaic.put(text_view),
        current_model=mosaic.put(text),
        layout_k=None,
        prev=None,
        next=None,
        )
    view = view_reg.animate(navigator_piece, ctx)
    state = htypes.text.state("")
    hook = Mock()
    splitter.split_horizontally(view, state, hook, ctx)
    hook.replace_view.assert_called_once()


def test_wrap():
    inner = htypes.label.view("Inner label")
    piece = splitter.wrap_splitter(inner)
    assert isinstance(piece, htypes.splitter.view)


@mark.config_fixture('view_factory_reg')
def view_factory_reg_config():
    k = htypes.splitter_tests.sample_k()
    factory = Mock()
    factory.call.return_value = htypes.label.view("Sample label")
    return {k: factory}
