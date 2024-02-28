from PySide6 import QtWidgets

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.list_diff import ListDiff
from .code.context import Context
from .code.command_hub import CommandHub
from .code.view import Diff
from .tested.code import tabs


def make_inner_layout():
    adapter_layout = htypes.str_adapter.static_str_adapter("Sample text")
    tab_layout = htypes.text.view_layout(mosaic.put(adapter_layout))
    return htypes.tabs.layout(
        tabs=[
            htypes.tabs.tab("One", mosaic.put(tab_layout))],
        )


def make_outer_layout(tab_layout):
    return htypes.tabs.layout(
        tabs=[
            htypes.tabs.tab("Inner", mosaic.put(tab_layout))],
        )


def make_inner_state():
    tab_state = htypes.text.state()
    return htypes.tabs.state(
        current_tab=0,
        tabs=[mosaic.put(tab_state)],
        )


def make_outer_state(tab_state):
    return htypes.tabs.state(
        current_tab=0,
        tabs=[mosaic.put(tab_state)],
        )


def test_tabs():
    ctx = Context(command_hub=CommandHub())
    piece = make_inner_layout()
    state = make_inner_state()
    app = QtWidgets.QApplication()
    try:
        view = tabs.TabsView.from_piece(piece)
        widget = view.construct_widget(state, ctx)
        assert view.piece
        state = view.widget_state(widget)
        assert state
    finally:
        app.shutdown()


def duplicate(layout, state):
    return Diff(
        piece=ListDiff.Insert(
            idx=state.current_tab + 1,
            item=layout.tabs[state.current_tab],
            ),
        state=ListDiff.Insert(
            idx=state.current_tab + 1,
            item=state.tabs[state.current_tab],
            ),
        )


def test_duplicate():
    ctx = Context(command_hub=CommandHub())
    piece = make_inner_layout()
    state = make_inner_state()
    app = QtWidgets.QApplication()
    try:
        view = tabs.TabsView.from_piece(piece)
        widget = view.construct_widget(state, ctx)
        diff = duplicate(piece, state)
        new_state, replace = view.apply(ctx, widget, diff)
        assert len(view.piece.tabs) == 2
        assert view.piece.tabs[0] == piece.tabs[0]
        assert view.piece.tabs[0] == view.piece.tabs[1]
    finally:
        app.shutdown()


def test_modify():
    ctx = Context(command_hub=CommandHub())
    inner_piece = make_inner_layout()
    outer_piece = make_outer_layout(inner_piece)
    inner_state = make_inner_state()
    outer_state = make_outer_state(inner_state)
    app = QtWidgets.QApplication()
    try:
        view = tabs.TabsView.from_piece(outer_piece)
        widget = view.construct_widget(outer_state, ctx)
        inner_diff = duplicate(inner_piece, inner_state)
        outer_diff = view.wrapper(widget, inner_diff)
        new_outer_state, replace = view.apply(ctx, widget, outer_diff)
        assert len(view.piece.tabs) == 1
        new_inner_piece = web.summon(view.piece.tabs[0].ctl)
        assert len(new_inner_piece.tabs) == 2
        assert new_inner_piece.tabs[0] == inner_piece.tabs[0]
        assert new_inner_piece.tabs[0] == new_inner_piece.tabs[1]
    finally:
        app.shutdown()
