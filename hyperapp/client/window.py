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

data_type = TRecord([
    Field('tab_view', tab_view.data_type),
    Field('size', size_type),
    Field('pos', point_type),
    ])


class Handle(composite.Handle):

    @classmethod
    def from_data( cls, rec ):
        return cls(tab_view.Handle.from_data(rec.tab_view),
                   size=QtCore.QSize(rec.size.w, rec.size.h),
                   pos=QtCore.QPoint(rec.pos.x, rec.pos.y))

    def __init__( self, child_handle, size=None, pos=None ):
        composite.Handle.__init__(self, [child_handle])
        self.child_handle = child_handle
        self.size = size
        self.pos = pos

    def to_data( self ):
        return data_type(
            tab_view=self.child_handle.to_data(),
            size=size_type(w=self.size.width(), h=self.size.height()),
            pos=point_type(x=self.pos.x(), y=self.pos.y()),
            )

    def get_child_handle( self ):
        return self.child_handle

    def construct( self, app ):
        log.info('window construct app=%r child_handle=%r', app, self.child_handle)
        return Window(app, self.child_handle, self.size, self.pos)

    def move( self, point ):
        return Handle(self.child_handle, self.size, self.pos + point)


class Window(composite.Composite, QtGui.QMainWindow):

    def __init__( self, app, child_handle, size=None, pos=None ):
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
        self.set_child(child_handle)
        self.show()
        self._parent().window_created(self)

    def closeEvent( self, evt ):
        QtGui.QMainWindow.closeEvent(self, evt)
        ## self.deleteLater()  # seems not required, at least when moved to QMainWindow from QWidget
        self._parent().window_closed(self)

    def handle( self ):
        return Handle(self._view.handle(), self.size(), self.pos())

    def get_current_child( self ):
        return self._view

    def replace_view( self, mapper ):
        handle = mapper(self._view.handle())
        if handle:
            self.set_child(handle)

    def set_child( self, handle ):
        self._view = handle.construct(self)
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
