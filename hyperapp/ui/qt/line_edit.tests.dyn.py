from unittest.mock import Mock

from . import htypes
from .services import (
    mosaic,
    )
from .code.mark import mark
from .code.context import Context
from .fixtures import qapp_fixtures
from .tested.code import line_edit



@mark.fixture
def ctx():
    return Context()


@mark.fixture
def adapter():
    return htypes.str_adapter.static_str_adapter()


@mark.fixture
def view_piece(adapter):
    return htypes.line_edit.readonly_view(mosaic.put(adapter))


@mark.fixture
def edit_piece(adapter):
    return htypes.line_edit.edit_view(mosaic.put(adapter))


@mark.fixture
def state():
    return htypes.line_edit.state('')


def test_edit_view(qapp, ctx, edit_piece, state):
    model = "Sample text"
    view = line_edit.EditLineView.from_piece(edit_piece, model, ctx)
    widget = view.construct_widget(state, ctx)
    assert view.piece == edit_piece
    state = view.widget_state(widget)
    assert state


def test_readonly_view(qapp, ctx, view_piece, state):
    model = "Sample text"
    view = line_edit.ViewLineView.from_piece(view_piece, model, ctx)
    widget = view.construct_widget(state, ctx)
    assert view.piece == view_piece
    state = view.widget_state(widget)
    assert state


def test_edit_factory():
    piece = line_edit.line_edit(adapter=None)
    assert piece


def test_opt_edit_factory():
    piece = line_edit.opt_line_edit(adapter=None)
    assert piece


def test_int_edit_factory():
    piece = line_edit.int_line_edit(adapter=None)
    assert piece


def test_view_factory():
    piece = line_edit.line_view(adapter=None)
    assert piece


def test_line_edit_resource_name(edit_piece):
    gen = Mock()
    gen.assigned_name.return_value = 'some-adapter'
    name = line_edit.line_edit_resource_name(edit_piece, gen)
    assert type(name) is str


def test_line_view_resource_name(view_piece):
    gen = Mock()
    gen.assigned_name.return_value = 'some-adapter'
    name = line_edit.line_view_resource_name(view_piece, gen)
    assert type(name) is str
