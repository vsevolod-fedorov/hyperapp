from unittest.mock import Mock

from . import htypes
from .code.context import Context
from .fixtures import qapp_fixtures
from .tested.code import command_pane


async def test_widget(qapp):
    ctx = Context(
        lcs=Mock(),
        )
    piece = htypes.command_pane.view()
    state = htypes.command_pane.state()
    command = Mock(
        d=htypes.command_pane_tests.sample_command_d(),
        groups={},
        enabled=True,
        )
    view = command_pane.CommandPaneView.from_piece(piece, ctx)
    widget = view.construct_widget(state, ctx)
    assert view.piece
    state = view.widget_state(widget)
    assert state
    rctx = Context(commands=[command])
    await view.children_changed(ctx, rctx, widget, save_layout=False)
