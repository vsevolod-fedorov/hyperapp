import logging
import weakref
from PySide2 import QtCore, QtWidgets

from hyperapp.common.util import is_list_inst
from hyperapp.client.util import DEBUG_FOCUS, call_after
from hyperapp.client.command import command
from hyperapp.client.module import ClientModule

from . import htypes
from .view import View
from .view_registry import RootVisualItem, ViewHandler
from .tab_view import TabView

log = logging.getLogger(__name__)

LOCALE = 'en'

DEFAULT_SIZE = QtCore.QSize(800, 800)
DUP_OFFSET = QtCore.QPoint(150, 50)

    
class WindowHandler(ViewHandler):

    @classmethod
    async def from_data(cls, state, path, view_resolver):
        self = cls(state, path)
        await self._async_init(view_resolver)
        return self

    def __init__(self, state, path):
        super().__init__()
        self._state = state
        self._path = path

    async def _async_init(self, view_resolver):
        self._menu_bar_handler = await view_resolver.resolve(self._state.menu_bar_ref, [*self._path, 0])
        self._command_pane_handler = await view_resolver.resolve(self._state.command_pane_ref, [*self._path, 1])
        self._central_view_handler = await view_resolver.resolve(self._state.central_view_ref, [*self._path, 2])

    async def create_view(self, command_registry, view_opener=None):
        menu_bar = await self._menu_bar_handler.create_view(command_registry)
        command_pane = await self._command_pane_handler.create_view(command_registry)
        central_view = await self._central_view_handler.create_view(command_registry)
        return Window(menu_bar, command_pane, central_view, self._state.size, self._state.pos)

    async def visual_item(self):
        menu_bar = await self._menu_bar_handler.visual_item()
        command_pane = await self._command_pane_handler.visual_item()
        central_view = await self._central_view_handler.visual_item()
        return RootVisualItem('Window', children=[
            menu_bar.to_item(0, 'menu_bar'),
            command_pane.to_item(1, 'command_pane'),
            central_view.to_item(2, 'central_view'),
            ])


class Window(View, QtWidgets.QMainWindow):

    def __init__(self, menu_bar, command_pane, central_view, size=None, pos=None):
        QtWidgets.QMainWindow.__init__(self)
        View.__init__(self)
        self._child_widget = None
        if size:
            self.resize(size.w, size.h)
        else:
            self.resize(DEFAULT_SIZE)
        if pos:
            self.move(pos.x, pos.y)
        else:
            self.move(800, 100)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, command_pane)
        self.setMenuWidget(menu_bar)
        self.setCentralWidget(central_view)

    def get_state(self):
        return htypes.window.window(
            tab_view=self._view.get_state(),
            size=htypes.window.size(w=self.width(), h=self.height()),
            pos=htypes.window.pos(x=self.x(), y=self.y()),
            )

    def get_current_child(self):
        return self._view

    ## def replace_view(self, mapper):
    ##     handle = mapper(self._view.handle())
    ##     if handle:
    ##         self.set_child(handle)

    def set_child(self, child):
        self._view = child
        child.set_parent(self)
        self.view_changed(self._view)

    def open(self, handle):
        self._view.open(handle)

    def object_selected(self, obj):
        return False

    def view_changed(self, view):
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
        self._command_pane.view_changed(self)
        #self._filter_pane.view_changed(self)

    def view_commands_changed(self, command_kinds):
        self._menu_bar.view_commands_changed(self, command_kinds)
        self._command_pane.view_commands_changed(self, command_kinds)
        
    @command('duplicate_window')
    async def duplicate_window(self):
        state = self.get_state()
        state.pos.x += DUP_OFFSET.x()
        state.pos.y += DUP_OFFSET.y()
        await self.from_state(state, self._app, self._module_command_registry, self._view_registry, self._resource_resolver)


class ThisModule(ClientModule):

    def __init__(self, module_name, services):
        super().__init__(module_name, services)
        services.view_registry.register_type(htypes.window.window, WindowHandler.from_data, services.view_resolver)
