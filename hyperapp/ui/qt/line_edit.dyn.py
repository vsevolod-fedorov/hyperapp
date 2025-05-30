from hyperapp.boot.htypes import TOptional

import logging
import weakref

from PySide6 import QtWidgets

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.mark import mark
from .code.view import View
from .code.type_convertor import type_to_text_convertor

log = logging.getLogger(__name__)


class LineInput:

    def __init__(self, view, widget):
        self._view = view
        self._widget_wr = weakref.ref(widget)

    def get_value(self):
        widget = self._widget_wr()
        if not widget:
            raise RuntimeError(f"Line input: widget for {self._view} is gone")
        return self._view.get_value(widget)


class EditLineView(View):

    @classmethod
    @mark.view
    def from_piece(cls, piece, model, ctx, ui_adapter_creg):
        adapter = ui_adapter_creg.invite(piece.adapter, model, ctx)
        return cls(piece.adapter, adapter)

    def __init__(self, adapter_ref, adapter):
        super().__init__()
        self._adapter_ref = adapter_ref
        self._adapter = adapter

    @property
    def piece(self):
        return htypes.line_edit.edit_view(self._adapter_ref)

    def construct_widget(self, state, ctx):
        w = QtWidgets.QLineEdit()
        if state:
            text = state.text
        else:
            text = self._adapter.get_view_value()
        w.setText(text)
        w.textEdited.connect(self._on_text_edited)
        return w

    def widget_state(self, widget):
        return htypes.line_edit.state(text=self.get_text(widget))

    def primary_parent_context(self, rctx, widget):
        return rctx.clone_with(
            model_state=self._model_state(widget),
            input=LineInput(self, widget),
            )

    def _model_state(self, widget):
        return self.get_text(widget)

    def get_text(self, widget):
        return widget.text()

    def get_value(self, widget):
        text = self.get_text(widget)
        return self._adapter.text_to_value(text)

    def _on_text_edited(self, text):
        self._adapter.value_changed_by_me(text)


class ViewLineView(EditLineView):

    @classmethod
    @mark.view
    def from_piece(cls, piece, model, ctx, ui_adapter_creg):
        adapter = ui_adapter_creg.invite(piece.adapter, model, ctx)
        return cls(piece.adapter, adapter)

    @property
    def piece(self):
        return htypes.line_edit.readonly_view(self._adapter_ref)

    def construct_widget(self, state, ctx):
        w = super().construct_widget(state, ctx)
        w.setReadOnly(True)
        return w


@mark.view_factory.model_t(htypes.builtin.string)
@mark.view_factory.model_t(TOptional(htypes.builtin.string))
@mark.view_factory.model_t(htypes.builtin.int)
def line_edit(model_t, accessor):
    cvt = type_to_text_convertor(model_t)
    adapter = htypes.value_adapter.value_adapter(
        accessor=mosaic.put(accessor),
        convertor=mosaic.put(cvt),
        )
    return htypes.line_edit.edit_view(
        adapter=mosaic.put(adapter),
        )


@mark.view_factory.model_t(htypes.builtin.string)
def line_view(model_t, accessor):
    cvt = type_to_text_convertor(model_t)
    adapter = htypes.value_adapter.value_adapter(
        accessor=mosaic.put(accessor),
        convertor=mosaic.put(cvt),
        )
    return htypes.line_edit.readonly_view(
        adapter=mosaic.put(adapter),
        )


@mark.actor.resource_name_creg
def line_edit_resource_name(piece, gen):
    adapter = web.summon(piece.adapter)
    adapter_name = gen.assigned_name(adapter)
    return f'line_edit-{adapter_name}'


@mark.actor.resource_name_creg
def line_view_resource_name(piece, gen):
    adapter = web.summon(piece.adapter)
    adapter_name = gen.assigned_name(adapter)
    return f'line_view-{adapter_name}'
