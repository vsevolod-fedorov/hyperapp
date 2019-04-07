import asyncio
from contextlib import suppress
import logging
import weakref

from PySide import QtCore, QtGui

from hyperapp.common.htypes import resource_key_t
from hyperapp.client.util import make_async_action
from hyperapp.client.command import Command
from hyperapp.client.module import ClientModule
from . import htypes
from .tree_object import TreeObserver, TreeObject
from .view import ViewCommand, View

log = logging.getLogger(__name__)


MODULE_NAME = 'tree_view'


class _Model(QtCore.QAbstractItemModel, TreeObserver):

    def __init__(self, view, resource_resolver, locale, resource_key, object):
        QtCore.QAbstractItemModel.__init__(self)
        TreeObserver.__init__(self)
        self._view_wr = weakref.ref(view)
        self._resource_resolver = resource_resolver
        self._locale = locale
        self._resource_key = resource_key
        self._object = object
        self._columns = object.get_columns()
        self._column2resource = {}
        self._item_id_attr = self._columns[0].id
        self._path2item = {}
        self._path2children = {}
        self._fetch_requested_for_path = set()  # do not issue fetch request when previous is not yet completed
        self._id2path = {}
        self._path2id = {}
        self._id_counter = 0
        self._load_resources()
        self._object.subscribe(self)

    # qt methods  -------------------------------------------------------------------------------------------------------

    def columnCount(self, index):
        return len(self._columns)

    def headerData(self, section, orient, role):
        if role == QtCore.Qt.DisplayRole and orient == QtCore.Qt.Orientation.Horizontal:
            column_id = self._columns[section].id
            resource = self._column2resource.get(column_id)
            if resource:
                return resource.text
            else:
                return column_id
        return QtCore.QAbstractTableModel.headerData(self, section, orient, role)

    def index(self, row, column, parent):
        parent_path = self.index2path(parent)
        log.debug('_Model.index(%s, %s, %s), id=%s, path=%s', row, column, parent, parent.internalId(), parent_path)
        item_list = self._path2children[parent_path]
        id = getattr(item_list[row], self._item_id_attr)
        path = parent_path + (id,)
        id = self._path2id.get(path)
        if id is None:
            id = self._get_next_id()
            self._path2id[path] = id
            self._id2path[id] = path
        return self.createIndex(row, column, id)

    def parent(self, index):
        path = self.index2path(index)
        if path and len(path) > 1:
            parent_id = self._path2id[path[:-1]]
            return self.createIndex(0, 0, parent_id)
        else:
            return QtCore.QModelIndex()

    def hasChildren(self, index):
        path = self.index2path(index)
        item_list = self._path2children.get(path)
        return item_list != []  # is empty item list already received for this path?

    def rowCount(self, index):
        path = self.index2path(index)
        item_list = self._path2children.get(path)
        if item_list is None:
            self._request_fetch(path)
            return 0
        else:
            return len(item_list)

    def data(self, index, role):
        if role != QtCore.Qt.DisplayRole:
            return None
        column = self._columns[index.column()]
        path = self._id2path.get(index.internalId())
        log.debug('_Model.data id=%d, row=%d column=%r path=%s', index.internalId(), index.row(), index.column(), path)
        if path is None:
            return None
        item = self._path2item[path]
        value = getattr(item, column.id)
        return str(value)

    def canFetchMore(self, parent):
        path = self.index2path(parent)
        result = path not in self._path2children
        log.debug('_Model.canFetchMore id=%d, row=%d column=%r path=%s, result=%s', parent.internalId(), parent.row(), parent.column(), path, result)
        return result

    def fetchMore(self, parent):
        path = self.index2path(parent)
        log.debug('_Model.fetchMore id=%d, row=%d column=%r path=%s already fetching=%s',
                  parent.internalId(), parent.row(), parent.column(), path, path in self._fetch_requested_for_path)
        self._request_fetch(path)

    # own methods  ------------------------------------------------------------------------------------------------------

    def _load_resources(self):
        for column in self._columns:
            resource_key = resource_key_t(self._resource_key.module_ref, self._resource_key.path + ['column', column.id])
            self._column2resource[column.id] = self._resource_resolver.resolve(resource_key, self._locale)

    def _request_fetch(self, path):
        if path not in self._fetch_requested_for_path:
            self._fetch_requested_for_path.add(path)
            log.info('  request fetch for %s', path)
            asyncio.ensure_future(self._object.fetch_items(path))

    def process_fetch_results(self, path, item_list):
        log.debug('fetched %d items at %s: %s', len(item_list), path, item_list)
        path = tuple(path)
        with suppress(KeyError):
            self._fetch_requested_for_path.remove(path)
        current_item_list = self._path2children.setdefault(path, [])
        prev_item_count = len(current_item_list)
        current_item_list += item_list
        for item in item_list:
            id = getattr(item, self._item_id_attr)
            self._path2item[path + (id,)] = item
        self.rowsInserted.emit(QtCore.QModelIndex(), prev_item_count + 1, len(current_item_list) - 1)
        for idx in range(len(self._columns)):
            self._view_wr().resizeColumnToContents(idx)

    def index2path(self, index):
        if index.isValid():
            return self._id2path[index.internalId()]
        else:
            return ()

    def _get_next_id(self):
        self._id_counter += 1
        return self._id_counter


class TreeView(View, QtGui.QTreeView):

    def __init__(self, resource_resolver, locale, parent, resource_key, object):
        QtGui.QTreeView.__init__(self)
        self.setModel(_Model(self, resource_resolver, locale, resource_key, object))
        View.__init__(self, parent)
        self.setSelectionMode(self.ContiguousSelection)
        self._resource_resolver = resource_resolver
        self._locale = locale
        self._resource_key = resource_key
        self._object = object
        self._elt_commands = []   # Command list - commands for selected elements
        self._elt_actions = []    # QtGui.QAction list - actions for selected elements
        self._default_command = None

    def get_state(self):
        return htypes.tree_view.tree_handle('tree', self._object.get_state(), self._resource_key)

    def get_object(self):
        return self._object

    def get_command_list(self, kinds):
        command_list = View.get_command_list(self, kinds)
        filtered_command_list = list(filter(lambda command: command.kind != 'element', command_list))
        if not kinds or 'element' in kinds:
            return filtered_command_list + self._elt_commands
        else:
            return filtered_command_list

    def currentChanged(self, idx, prev_idx):
        QtGui.QTreeView.currentChanged(self, idx, prev_idx)
        self._selected_items_changed()

    @property
    def _current_item_path(self):
        return self.model().index2path(self.currentIndex())

    def _selected_items_changed(self):
        self._update_selected_actions()
        if self.isVisible():  # we may being destructed now
            self.view_commands_changed(['element'])

    def _update_selected_actions(self):
        # remove previous actions
        action_widget = self
        for action in self._elt_actions:
            action_widget.removeAction(action)
        self._elt_actions.clear()
        self._elt_commands.clear()
        self._default_command = None
        # pick selection and commands
        item_path = self._current_item_path
        if item_path is None:
            return
        # create actions
        for command in self._object.get_item_command_list(item_path):
            assert isinstance(command, Command), repr(command)
            assert command.kind == 'element', repr(command)
            resource = self._resource_resolver.resolve(command.resource_key, self._locale)
            wrapped_command = self._wrap_item_command(item_path, command)
            action = make_async_action(
                action_widget, '%s/%s' % (wrapped_command.resource_key, wrapped_command.id),
                resource.shortcut_list if resource else None, wrapped_command.run)
            action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
            action_widget.addAction(action)
            self._elt_actions.append(action)
            self._elt_commands.append(wrapped_command)
            if resource and resource.is_default:
                self._default_command = wrapped_command

    def _wrap_item_command(self, item_path, command):
        return ViewCommand.from_command(command, self, item_path)

    def __del__(self):
        log.debug('~tree_view.TreeView self=%r', id(self))


class ThisModule(ClientModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME, services)
        self._resource_resolver = services.resource_resolver
        services.tree_view_factory = self._tree_view_factory
        services.view_registry.register('tree', self._tree_view_from_state, services.objimpl_registry)

    async def _tree_view_from_state(self, locale, state, parent, objimpl_registry):
        object = await objimpl_registry.resolve_async(state.object)
        return self._tree_view_factory(locale, parent, state.resource_key, object)

    def _tree_view_factory(self, locale, parent, resource_key, object):
        return TreeView(self._resource_resolver, locale, parent, resource_key, object)
