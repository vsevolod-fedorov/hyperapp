from PySide import QtCore, QtGui

from hyperapp.client.module import ClientModule
from .tree_object import TreeObject
from .view import View


MODULE_NAME = 'tree_view'


class _Model(QtCore.QAbstractItemModel):

    def __init__(self, resource_resolver, locale, resource_key, object):
        super().__init__()
        self._resource_resolver = resource_resolver
        self._locale = locale
        self._resource_key = resource_key
        self._object = object
        self._columns = object.get_columns()
        self._path2nodes = {}
        self._id2path = {}

    def columnCount(self, index):
        return len(self._columns)

    def headerData(self, section, orient, role):
        if role == QtCore.Qt.DisplayRole and orient == QtCore.Qt.Orientation.Horizontal:
            column_id = self._visible_columns[section].id
            resource = self._column2resource.get(column_id)
            if resource:
                return resource.text
            else:
                return column_id
        return QtCore.QAbstractTableModel.headerData(self, section, orient, role)

    def rowCount(self, index):
        assert parent.column() == 0, repr(parent.column())
        path = self.id2path.get(index.internalId())
        if not path:
            return 0
        node_list = self._path2nodes[path]
        return len(node_list)

    def data( self, index, role ):
        if role != QtCore.Qt.DisplayRole:
            return None
        column = self._columns[index.column()]
        path = self.id2path.get(index.internalId())
        if not path:
            return None
        node_list = self._path2nodes[path]
        node = node_list[index.row()]
        value = getattr(node.row, column.id)
        return str(value)


class TreeView(View, QtGui.QTreeView):

    def __init__(self, resource_resolver, locale, parent, resource_key, object):
        QtGui.QTreeView.__init__(self)
        View.__init__(self, parent)
        self.setModel(_Model(resource_resolver, locale, resource_key, object))


class ThisModule(ClientModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME, services)
        self._resource_resolver = services.resource_resolver
        services.tree_view_factory = self._tree_view_factory

    def _tree_view_factory(self, locale, parent, resource_key, object):
        return TreeView(self._resource_resolver, locale, parent, resource_key, object)
