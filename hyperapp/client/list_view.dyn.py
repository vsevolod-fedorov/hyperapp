import abc
import sys
import logging
import bisect
import weakref
from functools import partial

from PySide2 import QtCore, QtGui, QtWidgets

from hyperapp.common.htypes.deduce_value_type import deduce_value_type
from hyperapp.client.util import uni2str, key_match, key_match_any, make_async_action
from hyperapp.common.logger import log, create_context_task
from hyperapp.client.module import ClientModule

from . import htypes
from .list_object import ListObserver, ListObject
from .layout import RootVisualItem, ObjectLayout
from .view import View
from .items_view import map_columns_to_view

_log = logging.getLogger(__name__)


ROW_HEIGHT_PADDING = 3  # same as default QTreeView padding


class _Model(QtCore.QAbstractTableModel, ListObserver):

    def __init__(self, view, columns, object):
        QtCore.QAbstractTableModel.__init__(self)
        self._view_wr = weakref.ref(view)
        self._object = object
        self._columns = columns
        self._key_attr = object.key_attribute
        self._fetch_pending = False  # has pending fetch request; do not issue more than one request at a time
        self._item_list = []
        self._eof = False
        self._id2index = {}
        self._object.subscribe(self)

    # qt methods  -------------------------------------------------------------------------------------------------------

    def columnCount(self, parent):
        return len(self._columns)

    def headerData(self, section, orient, role):
        if role == QtCore.Qt.DisplayRole and orient == QtCore.Qt.Orientation.Horizontal:
            return self._columns[section].title
        return QtCore.QAbstractTableModel.headerData(self, section, orient, role)

    def rowCount(self, parent):
        return len(self._item_list)

    def data(self, index, role):
        if role != QtCore.Qt.DisplayRole:
            return None
        column = self._columns[index.column()]
        item = self._item_list[index.row()]
        value = getattr(item, column.id)
        if value is None:
            return ''
        else:
            return str(value)

    def canFetchMore(self, parent):
        _log.debug('_Model.canFetchMore row=%d column=%r eof=%s', parent.row(), parent.column(), self._eof)
        return not self._eof

    def fetchMore(self, parent):
        _log.debug('_Model.fetchMore row=%d column=%r fetch pending=%s', parent.row(), parent.column(), self._fetch_pending)
        self._fetch_more()

    # own methods  ------------------------------------------------------------------------------------------------------

    def has_rows(self):
        return bool(self._item_list)

    def _fetch_more(self):
        assert not self._eof
        if self._fetch_pending:
            return
        if self._item_list:
            from_key = getattr(self._item_list[-1], self._key_attr)
        else:
            from_key = None
        _log.info('  requesting fetch from %r', from_key)
        create_context_task(self._object.fetch_items(from_key), log.fetch_more)
        self._fetch_pending = True

    def process_fetch_results(self, item_list, fetch_finished):
        _log.debug('fetched %d items (finished=%s): %s', len(item_list), fetch_finished, item_list)
        prev_items_len = len(self._item_list)
        self.beginInsertRows(QtCore.QModelIndex(), len(self._item_list), prev_items_len + len(item_list) - 1)
        self._item_list += item_list
        self._id2index.update({
            getattr(item, self._key_attr): self.createIndex(prev_items_len + i, 0)
            for i, item in enumerate(item_list)})
        self.endInsertRows()
        view = self._view_wr()
        if view:
            view._on_data_changed()
        if fetch_finished:
            self._fetch_pending = False
        if fetch_finished and not self._eof and view and view._wanted_current_id is not None:
            # item we want to set as current is not fetched yet
            self._fetch_more()

    def process_eof(self):
        _log.debug('reached eof')
        self._eof = True

    def index2id(self, index):
        if not index.isValid():
            return None
        item = self._item_list[index.row()]
        return getattr(item, self._key_attr)

    def id2index(self, item_id):
        return self._id2index.get(item_id)

    def __del__(self):
        _log.info('~list_view.Model self=%s', id(self))


class ListViewObserver(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def current_changed(self, current_key):
        pass


class ListView(View, ListObserver, QtWidgets.QTableView):

    def __init__(self, columns, object, key=None):
        self._observers = weakref.WeakSet()
        self._elt_actions = []    # QtGui.QAction list - actions for selected elements
        QtWidgets.QTableView.__init__(self)
        self.setModel(_Model(self, columns, object))
        View.__init__(self)
        self._object = object
        self._wanted_current_id = key  # will set it to current when rows are loaded
        self._default_command = None
        self.verticalHeader().hide()
        opts = self.viewOptions()
        self.verticalHeader().setDefaultSectionSize(QtGui.QFontInfo(opts.font).pixelSize() + ROW_HEIGHT_PADDING)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(False)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.SingleSelection)
        self.activated.connect(self._on_activated)

    # obsolete
    def get_state(self):
        return self._data_type('list', self._object.get_state(), self._resource_key, self.current_item_key)

    def get_object(self):
        return self._object

    def add_observer(self, observer):
        self._observers.add(observer)

    def keyPressEvent(self, evt):
        if key_match_any(evt, ['Tab', 'Backtab', 'Ctrl+Tab', 'Ctrl+Shift+Backtab']):
            evt.ignore()  # let splitter or tab view handle it
            return
        QtWidgets.QTableView.keyPressEvent(self, evt)

    def currentChanged(self, idx, prev_idx):
        log.current_changed(row=idx.row())
        QtWidgets.QTableView.currentChanged(self, idx, prev_idx)
        current_key = self.current_item_key
        for observer in self._observers:
            observer.current_changed(current_key)

    @property
    def current_item_key(self):
        return self.model().index2id(self.currentIndex())

    def _on_data_changed(self):
        self.resizeColumnsToContents()
        if self._wanted_current_id is not None:
            index = self.model().id2index(self._wanted_current_id)
        else:
            if self.currentIndex().isValid():
                return
            elif self.model().has_rows():
                # ensure at least one item is selected
                index = self.model().createIndex(0, 0)
            else:
                return
        self.setCurrentIndex(index)
        self.scrollTo(index)
        self._wanted_current_id = None

    def _on_activated(self, index):
        if self._default_command:
            create_context_task(self._default_command.run(), log.activated)

    # def __del__(self):
    #     _log.debug('~list_view.ListView self=%r', id(self))


class ListViewLayout(ObjectLayout):

    class _CurrentItemObserver:

        def __init__(self, layout, command_hub):
            self._layout = layout
            self._command_hub = command_hub

        def current_changed(self, current_item_key):
            self._layout._update_element_commands(self._command_hub, current_item_key)

    def __init__(self, type_resolver, resource_resolver, params_editor, object, path):
        super().__init__(path)
        self._type_resolver = type_resolver
        self._resource_resolver = resource_resolver
        self._params_editor = params_editor
        self._object = object
        self._current_item_observer = None

    @property
    def data(self):
        return htypes.list_view.list_layout()

    async def create_view(self, command_hub):
        columns = list(map_columns_to_view(self._resource_resolver, self._object))
        list_view = ListView(columns, self._object)
        self._current_item_observer = observer = self._CurrentItemObserver(self, command_hub)
        list_view.add_observer(observer)
        return list_view

    async def visual_item(self):
        return RootVisualItem('ListView')

    def get_current_commands(self, view):
        object_command_it = self._get_object_commands()
        current_key = view.current_item_key
        if current_key is not None:
            return [*object_command_it, *self._get_element_commands(current_key)]
        else:
            return list(object_command_it)

    def collect_view_commands(self):
        return {
            **super().collect_view_commands(),
            **{tuple(self._path): self._get_object_commands()},
            }

    def _get_object_commands(self):
        return self._object.get_command_list()

    def _update_element_commands(self, command_hub, current_item_key):
        command_hub.update(only_kind='element')

    def _get_element_commands(self, current_item_key):
        for command in self._object.get_item_command_list(current_item_key):
            yield command.partial(current_item_key)


class ThisModule(ClientModule):

    def __init__(self, module_name, services):
        super().__init__(module_name, services)
        self._type_resolver = services.type_resolver
        self._resource_resolver = services.resource_resolver
        self._params_editor = services.params_editor
        services.default_object_layouts.register('list', ListObject.category_list, self._make_list_layout_rec)
        services.available_object_layouts.register('list', ListObject.category_list, self._make_list_layout_rec)
        services.object_layout_registry.register_type(htypes.list_view.list_layout, self._produce_layout)

    async def _make_list_layout_rec(self, object):
        return htypes.list_view.list_layout()

    async def _produce_layout(self, state, object):
        return ListViewLayout(self._type_resolver, self._resource_resolver, self._params_editor, object, [])
