import logging
from functools import partial

from PySide6 import QtCore, QtWidgets

from . import htypes
from .code.mark import mark
from .code.list_diff import IndexListDiff
from .code.view import View

log = logging.getLogger(__name__)


ROW_HEIGHT_PADDING = 3  # same as default QTreeView padding


class _Model(QtCore.QAbstractTableModel):

    def __init__(self, adapter):
        super().__init__()
        self.adapter = adapter
        self.adapter.subscribe(self)

    # Qt methods  -------------------------------------------------------------------------------------------------------

    def columnCount(self, parent):
        return self.adapter.column_count()

    def headerData(self, section, orient, role):
        if role == QtCore.Qt.DisplayRole and orient == QtCore.Qt.Orientation.Horizontal:
            return self.adapter.column_title(section)
        return super().headerData(section, orient, role)

    def rowCount(self, parent):
        return self.adapter.row_count()

    def data(self, index, role):
        if role != QtCore.Qt.DisplayRole:
            return None
        value = self.adapter.cell_data(index.row(), index.column())
        if value is None:
            return ""
        else:
            return str(value)

    # subscription  ----------------------------------------------------------------------------------------------------

    def process_diff(self, diff):
        log.info("List: process diff: %s", diff)
        if isinstance(diff, IndexListDiff.Append):
            row_count = self.adapter.row_count()
            self.beginInsertRows(QtCore.QModelIndex(), row_count - 1, row_count - 1)
            self.endInsertRows()
        elif isinstance(diff, IndexListDiff.Replace):
            left = self.createIndex(diff.idx, 0)
            right = self.createIndex(diff.idx, self.adapter.column_count() - 1)
            self.dataChanged.emit(left, right)
        elif isinstance(diff, IndexListDiff.Remove):
            self.beginRemoveRows(QtCore.QModelIndex(), diff.idx, diff.idx)
            self.endRemoveRows()
        else:
            raise NotImplementedError(diff)


class _TableView(QtWidgets.QTableView):

    def __init__(self):
        super().__init__()
        self._focusable = False
        self._on_state_changed = None

    def init_widget(self, focusable, on_state_changed):
        self._focusable = focusable
        self._on_state_changed = on_state_changed
        if focusable and self.isVisible():
            self.setFocus()

    def currentChanged(self, current, previous):
        result = super().currentChanged(current, previous)
        if self._on_state_changed:
            self._on_state_changed()
        return result

    def setVisible(self, visible):
        if not self._focusable:
            # Something sets policy back to strong policy if policy is set in init_widget.
            self.setFocusPolicy(QtCore.Qt.NoFocus)
        super().setVisible(visible)
        if visible and self._focusable:
            self.setFocus()

    # When opened in splitter, show which pane is active using selection.
    def focusInEvent(self, event):
        self.selectRow(self.currentIndex().row())
        return super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.clearSelection()
        return super().focusOutEvent(event)


class ListView(View):

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
        return htypes.list.view(self._adapter_ref)

    def construct_widget(self, state, ctx):
        widget = _TableView()
        model = _Model(self._adapter)
        widget.setModel(model)
        widget.verticalHeader().hide()
        widget.setShowGrid(False)
        widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        widget.setTabKeyNavigation(False)
        font_info = widget.fontInfo()
        widget.verticalHeader().setDefaultSectionSize(font_info.pixelSize() + ROW_HEIGHT_PADDING)
        widget.setCurrentIndex(widget.model().createIndex(0, 0))
        widget.resizeColumnsToContents()
        # model.dataChanged.connect(partial(self._on_data_changed, widget))
        self._apply_state(widget, state)
        widget.clearSelection()
        model.rowsInserted.connect(partial(self._on_data_changed, widget))
        return widget

    def init_widget(self, widget, focusable):
        widget.init_widget(focusable, on_state_changed=self._ctl_hook.parent_context_changed)

    def make_widget_state(self, key):
        return self._adapter.make_list_state(key)

    def widget_state(self, widget):
        idx = widget.currentIndex().row()
        return htypes.list.state(current_idx=idx)

    def set_current_key(self, widget, key):
        state = self._adapter.make_list_state(key)
        self._apply_state(widget, state)

    def _apply_state(self, widget, state):
        if isinstance(state, htypes.list.state):
            index = widget.model().createIndex(state.current_idx, 0)
            widget.setCurrentIndex(index)

    def primary_parent_context(self, rctx, widget):
        return rctx.clone_with(
            model_state=self._model_state(widget),
            )

    def _model_state(self, widget):
        idx = widget.currentIndex().row()
        if idx == -1 or idx >= self._adapter.row_count():
            return None
        current_item = self._adapter.get_item(idx)
        return self._adapter.make_model_state(current_idx=idx, current_item=current_item)

    @property
    def adapter(self):
        return self._adapter

    def _on_data_changed(self, widget, *args):
        log.info("List: on_data_changed: %s: %s", widget, args)
        widget.resizeColumnsToContents()
