import sys
from PySide import QtCore, QtGui

sys.path.append('..')

from util import uni2str, key_match, key_match_any
from list_object import ListDiff, ListObject
from command import run_element_command, make_element_cmd_action
import view


ROW_HEIGHT_PADDING = 3  # same as default QTreeView padding


class Handle(view.Handle):

    def __init__( self, object, key=None, selected_keys=None, select_first=True ):
        view.Handle.__init__(self)
        self.object = object
        self.key = key
        self.selected_keys = selected_keys  # for multi-select mode only
        self.select_first = select_first  # bool

    def get_object( self ):
        return self.object

    def construct( self, parent ):
        print 'list_view construct', parent, self.object.get_title(), self.object, repr(self.key)
        return View(parent, self.object, self.key, self.selected_keys, self.select_first)

    def __repr__( self ):
        return 'list_view.Handle(%s, %s)' % (uni2str(self.object.get_title()), uni2str(self.key))


class OrderedElements(object):

    def __init__( self, bof, eof, keys ):
        self.bof = bof
        self.eof = eof
        self.keys = keys


class Model(QtCore.QAbstractTableModel):

    def __init__( self ):
        QtCore.QAbstractTableModel.__init__(self)
        self._object = None
        self._columns = []
        self._visible_columns = []
        self._key2element = {}
        self._current_order = None  # column id
        self._ordered = {}  # order column id -> OrderedElements

    def element_count( self ):
        return self._object.element_count()

    def diff_applied( self, diff ):
        print '--- list_view.Model.diff_applied', diff
        return
        ## self._update_mapping()  # underlying list object elements are already changed
        ## if diff.start_key is not None:
        ##     assert diff.start_key == diff.end_key  # only signle key removal is supported by now
        ##     elements = self._object.get_fetched_elements()
        ##     if elements and elements[0].key < elements[-1].key:
        ##         for row, elt in enumerate(elements):
        ##             if elt.key > diff.start_key:
        ##                 self.rowsRemoved.emit(QtCore.QModelIndex(), row, row)
        ##                 break
        ##     else:
        ##         for row, elt in enumerate(elements):
        ##             if elt.key < diff.start_key:
        ##                 self.rowsRemoved.emit(QtCore.QModelIndex(), row, row)
        ##                 break
        ##     assert diff.end_key is not None
        ##     start_row = self._key2row[diff.start_key]
        ##     end_row = self._key2row[diff.end_key]
        ##     self.rowsRemoved.emit(QtCore.QModelIndex(), start_row, end_row)
        ## if diff.start_key is not None and diff.elements:
        ##     start_row = self._key2row[diff.start_key]
        ##     self.rowsInserted.emit(QtCore.QModelIndex(), start_row + 1, start_row + len(diff.elements))
        ## if diff.start_key == None and diff.end_key == None:  # append
        ##     element_count = self._object.element_count()
        ##     self.rowsInserted.emit(QtCore.QModelIndex(), element_count - len(diff.elements), element_count - 1)

    def data( self, index, role ):
        if role == QtCore.Qt.DisplayRole:
            column = self._visible_columns[index.column()]
            key = self._current_ordered().keys[index.row()]
            element = self._get_key2element(key)
            value = getattr(element.row, column.id)
            return column.type.to_string(value)
        return None

    def headerData( self, section, orient, role ):
        if role == QtCore.Qt.DisplayRole and orient == QtCore.Qt.Orientation.Horizontal:
            return self._visible_columns[section].title
        hdata = QtCore.QAbstractTableModel.headerData(self, section, orient, role)
        return hdata

    def rowCount( self, parent ):
        if parent == QtCore.QModelIndex() and self._object:
            return len(self._current_ordered().keys)
        else:
            return 0

    def columnCount( self, parent ):
        if parent == QtCore.QModelIndex() and self._object:
            return len(self._visible_columns)
        else:
            return 0

    def reset( self ):
        ## self._update_mapping()
        QtCore.QAbstractTableModel.reset(self)

    def set_object( self, object ):
        self._object = object
        self._columns = object.get_columns()
        self._visible_columns = filter(lambda column: column.title is not None, self._columns)
        self._key_column_id = object.get_key_column_id()
        self._current_order = object.sorted_by_column
        self._update_elements(object.elements)
        self._ordered[self._current_order] = OrderedElements(
            object.bof, object.eof, [self._element2key(element) for element in object.elements])
        self.reset()

    def visible_rows_changed( self, first_visible_row, visible_row_count ):
        wanted_last_row = first_visible_row + visible_row_count + 1
        ordered = self._current_ordered()
        wanted_rows = wanted_last_row - len(ordered.keys)
        if wanted_rows > 0:
            self._object.fetch_elements(self._current_order, ordered.keys[-1], 0, wanted_rows)

    def _update_elements( self, elements ):
        for element in elements:
            self._key2element[self._element2key(element)] = element

    def _element2key( self, element ):
        return getattr(element.row, self._key_column_id)

    def _current_ordered( self ):
        return self._ordered[self._current_order]

    def _get_key2element( self, key ):
        return self._key2element[key]

    def __del__( self ):
        print '~list_view.Model'


class View(view.View, QtGui.QTableView):

    def __init__( self, parent, obj, key, selected_keys, select_first ):
        QtGui.QTableView.__init__(self)
        view.View.__init__(self, parent)
        self._select_first = select_first
        self._object = None
        self.setModel(Model())
        self.verticalHeader().hide()
        opts = self.viewOptions()
        self.verticalHeader().setDefaultSectionSize(QtGui.QFontInfo(opts.font).pixelSize() + ROW_HEIGHT_PADDING)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(False)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.SingleSelection)
        self.verticalScrollBar().valueChanged.connect(self.vscrollValueChanged)
        self.activated.connect(self._on_activated)
        self._selected_elt = None  # must keep own reference because it may change/disappear independently
        self._elt_actions = []    # QtGui.QAction list - actions for selected elements
        self.want_current_key = None
        self.set_object(obj)
        if not self.set_current_key(key, select_first):
            self.want_current_key = key  # need to fetch elements until this key is fount

    def handle( self ):
        return Handle(self.get_object(), self.get_current_key(), self.selected_keys(), self._select_first)

    def get_title( self ):
        if self._object:
            return self._object.get_title()

    def get_object( self ):
        return self._object

    def object_changed( self ):
        old_key = self._selected_elt.key if self._selected_elt else None
        self.model().reset()
        ## self.reset()  # selection etc must be cleared
        row = self.model().key2row(old_key)
        if row is None and self._object.element_count() > 0:
            # find next or any nearby row
            for row, element in enumerate(self._object.get_fetched_elements()):
                if element.key >= old_key:
                    break  # use this row
            # else: just use last row
        if row is not None:
            self.set_current_row(row)
        view.View.object_changed(self)
        self.check_if_elements_must_be_fetched()

    def process_fetch_result( self, result ):
        print 'process_fetch_result', result

    def diff_applied( self, diff ):
        #assert isinstance(diff, ListDiff), repr(diff)  # may also be interface update record
        self.model().diff_applied(diff)
        self._find_wanted_current_key()
        # may be this was response from elements fetching, but we may need more elements
        self.check_if_elements_must_be_fetched()

    def _find_wanted_current_key( self ):
        if self.set_current_key(self.want_current_key):
            self.want_current_key = None

    def get_current_key( self ):
        if self._selected_elt:
            return self._selected_elt.key
        else:
            return None

    def get_current_elt( self ):
        return self._selected_elt

    def get_selected_elts( self ):
        return filter(None, [self.get_current_elt()])  # [] if no selection

    def is_in_multi_selection_mode( self ):
        return False  # todo

    def set_current_row( self, row ):
        if row is not None:
            idx = self.model().createIndex(row, 0)
            self.setCurrentIndex(idx)
            self.scrollTo(idx)

    def set_current_key( self, key, select_first=False, accept_near=False ):
        ## if accept_near:
        ##     row = self._find_nearest_key(key)
        ## else:
        ##     row = self.model().key2row(key)
        ##     if row is None and select_first and self._object.get_fetched_elements():
        ##         row = 0
        ## if row is None:
        ##     return False
        ## self.set_current_row(row)
        return True

    def _find_nearest_key( self, key ):
        for idx, element in enumerate(self._object.get_fetched_elements()):
            if element.key >= key:
                return idx
        if self._object.get_fetched_elements():
            return 0
        else:
            return None  # has no rows

    def selected_keys( self ):
        return None

    def set_object( self, object ):
        assert isinstance(object, ListObject), repr(object)
        self._object = object
        self.model().set_object(object)
        self.resizeColumnsToContents()
        self._object.subscribe(self)

    def keyPressEvent( self, evt ):
        if key_match_any(evt, ['Tab', 'Backtab', 'Ctrl+Tab', 'Ctrl+Shift+Backtab']):
            evt.ignore()  # let splitter or tab view handle it
            return
        QtGui.QTableView.keyPressEvent(self, evt)

    def vscrollValueChanged( self, value ):
        self.check_if_elements_must_be_fetched()

    def resizeEvent( self, evt ):
        result = QtGui.QTableView.resizeEvent(self, evt)
        first_visible_row, visible_row_count = self._get_visible_rows()
        self.model().visible_rows_changed(first_visible_row, visible_row_count)
        return result

    def currentChanged( self, idx, prev_idx ):
        QtGui.QTableView.currentChanged(self, idx, prev_idx)
        ## if idx.row() != -1:
        ##     self._selected_elt = self._object.get_fetched_elements()[idx.row()]
        ## else:
        ##     self._selected_elt = None
        ## self._selected_elements_changed()

    def setVisible( self, visible ):
        QtGui.QTableView.setVisible(self, visible)
        if visible:
            self.selected_elements_changed(self.get_selected_elts())

    def _get_visible_rows( self ):
        first_visible_row = self.verticalHeader().visualIndexAt(0)
        row_height = self.verticalHeader().defaultSectionSize()
        visible_row_count = self.viewport().height() / row_height
        return (first_visible_row, visible_row_count)

    ## def check_if_elements_must_be_fetched( self ):
    ##     last_visible_row = self.get_last_visible_row()
    ##     want_element_count = last_visible_row + 1
    ##     force_load = self.want_current_key is not None
    ##     self._object.need_elements_count(last_visible_row + 1, force_load)

    def _on_activated( self, index ):
        elt = self._object.get_fetched_elements()[index.row()]
        for cmd in elt.commands:
            if cmd.id == 'open':
                run_element_command(cmd, self, elt.key)
                return

    def _selected_elements_changed( self ):
        self._update_selected_actions()
        if self.isVisible():  # we may being destructed now
            self.selected_elements_changed([self.get_current_elt()])

    def _update_selected_actions( self ):
        # remove previous actions
        action_widget = self
        for action in self._elt_actions:
            action_widget.removeAction(action)
        self._elt_actions = []
        # pick selection and commands
        elt = self.get_current_elt()
        if not elt: return
        element_key = elt.key
        commands = elt.commands
        # create actions
        for cmd in commands:
            action = make_element_cmd_action(cmd, action_widget, self, element_key)
            action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
            action_widget.addAction(action)
            self._elt_actions.append(action)

    def __del__( self ):
        print '~list_view.View', self
