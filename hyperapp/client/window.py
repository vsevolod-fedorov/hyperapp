import logging
import weakref
from PySide import QtCore, QtGui
from ..common.util import is_list_inst
from ..common.htypes import tInt, Field, TRecord, Interface
#from ..common.request import Request
from .util import DEBUG_FOCUS, call_after
from .view_command import command
from . import view
from . import composite
from .menu_bar import MenuBar
from . import cmd_pane
from . import tab_view

log = logging.getLogger(__name__)


DEFAULT_SIZE = QtCore.QSize(800, 800)
DUP_OFFSET = QtCore.QPoint(150, 50)


point_type = TRecord([
    Field('x', tInt),
    Field('y', tInt),
    ])

size_type = TRecord([
    Field('w', tInt),
    Field('h', tInt),
    ])

state_type = TRecord([
    Field('tab_view', tab_view.state_type),
    Field('size', size_type),
    Field('pos', point_type),
    ])


class Window(composite.Composite, QtGui.QMainWindow):

    @classmethod
    def from_state( cls, app, state ):
        return cls(app, state.tab_view,
                   size=QtCore.QSize(state.size.w, state.size.h),
                   pos=QtCore.QPoint(state.pos.x, state.pos.y))

    def __init__( self, app, child_state, size=None, pos=None ):
        assert isinstance(child_state, tab_view.state_type), repr(child_state)
        QtGui.QMainWindow.__init__(self)
        composite.Composite.__init__(self, app)
        self._app = app  # alias for _parent()
        self._view = None
        self._child_widget = None
        if size:
            self.resize(size)
        else:
            self.resize(DEFAULT_SIZE)
        if pos:
            self.move(pos)
        else:
            self.move(800, 100)
        self._menu_bar = MenuBar(app, weakref.ref(self))
        self._cmd_pane = cmd_pane.View(self)
        #self._filter_pane = filter_pane.View(self)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._cmd_pane)
        #self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._filter_pane)
        self.set_child(child_state)
        self.show()
        self._parent().window_created(self)

    def closeEvent( self, evt ):
        QtGui.QMainWindow.closeEvent(self, evt)
        ## self.deleteLater()  # seems not required, at least when moved to QMainWindow from QWidget
        self._parent().window_closed(self)

    def get_state( self ):
        return state_type(
            tab_view=self._view.get_state(),
            size=size_type(w=self.width(), h=self.height()),
            pos=point_type(x=self.x(), y=self.y()),
            )

    def get_current_child( self ):
        return self._view

    def replace_view( self, mapper ):
        handle = mapper(self._view.handle())
        if handle:
            self.set_child(handle)

    def set_child( self, child_state ):
        self._view = tab_view.View.from_state(self, child_state)
        self.view_changed(self._view)

    def open( self, handle ):
        self._view.open(handle)

    def selected_elements_changed( self, elts ):
        call_after(self._menu_bar.selected_elements_changed, elts)
        self._cmd_pane.selected_elements_changed(elts)
        #self._filter_pane.selected_elements_changed(elts)

    def object_selected( self, obj ):
        return False

    def view_changed( self, view ):
        assert view is self._view
        w = self._view.get_widget()
        if w is not self._child_widget:
            if DEBUG_FOCUS: log.info('*** window.view_changed: replacing widget self=%r view=%r w=%r old-w=%r', self, view, w, self._child_widget)
            if self._child_widget:
                self._child_widget.deleteLater()
            self.setCentralWidget(w)
            self._child_widget = w
        self.setWindowTitle(view.get_title())
        self._menu_bar.view_changed(self)
        self._cmd_pane.view_changed(self)
        #self._filter_pane.view_changed(self)

    @command('Duplicate window', 'Duplicate window', 'Alt+Shift+W')
    def duplicate_window( self ):
        self.handle().move(DUP_OFFSET).construct(self._parent())

    def __del__( self ):
        log.info('~window')
