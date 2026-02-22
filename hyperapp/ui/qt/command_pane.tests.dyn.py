from unittest.mock import Mock

from . import htypes
from .services import (
    pyobj_creg,
    )
from .code.context import Context
from .fixtures import qapp_fixtures
from .tested.code import command_pane


async def test_widget(qapp):
    piece = htypes.command_pane.view()
    state = htypes.command_pane.state()
    command_key = htypes.command.model_command_key(
        model_t=pyobj_creg.actor_to_ref(htypes.command_pane_tests.sample_model),
        name='sample_context_command',
        ),
    command = Mock(
        key=command_key,
        name='sample_context_command',
        )
    ctx = Context(
        piece=piece,
        )
    view = command_pane.CommandPaneView.from_piece(ctx)
    widget = view.construct_widget(state, ctx)
    assert view.piece
    state = view.widget_state(widget)
    assert state
    rctx = Context(commands=[command])
    await view.children_changed(ctx, rctx, widget, save_layout=False)
