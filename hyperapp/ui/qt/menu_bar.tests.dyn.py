from unittest.mock import Mock

from . import htypes
from .services import (
    pyobj_creg,
    )
from .code.context import Context
from .fixtures import qapp_fixtures
from .tested.code import menu_bar


def make_piece():
    return htypes.menu_bar.view()


def make_state():
    return htypes.menu_bar.state()


async def test_widget(command_factory, qapp):
    piece = make_piece()
    state = make_state()
    ctx = Context(
        piece=piece,
        )
    command = command_factory(
        key=htypes.command.ui_command_key(
            view_t=pyobj_creg.actor_to_ref(htypes.menu_bar_tests.sample_view),
            name='sample_command',
            ),
        name='sample_command',
        command=htypes.menu_bar_tests.sample_command(),
        ctx=ctx,
        )

    view = menu_bar.MenuBarView.from_piece(ctx)
    widget = view.construct_widget(state, ctx)
    assert view.piece
    state = view.widget_state(widget)
    assert state
    rctx = Context(commands=[command])
    await view.children_changed(ctx, rctx, widget, save_layout=False)
