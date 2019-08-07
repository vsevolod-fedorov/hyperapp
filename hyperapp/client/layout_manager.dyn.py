import asyncio
import logging
from functools import partial

from PySide import QtCore, QtGui

from hyperapp.common.htypes import resource_key_t
from hyperapp.client.util import make_async_action
from hyperapp.client.module import ClientModule
from .text_object import TextObject
from .text_view import TextView
from .tab_view import TabView
from .window import Window
from .list_object import ListObject
from .list_view import ListView
from .tree_object import TreeObject
from .tree_view import TreeView

_log = logging.getLogger(__name__)

MODULE_NAME = 'layout_manager'


class _CurrentItemObserver:

    def __init__(self, layout_manager, object):
        self._layout_manager = layout_manager
        self._object = object

    def current_changed(self, current_item_key):
        self._layout_manager.update_element_commands(self._object, current_item_key)


class History:

    def __init__(self):
        self._backward = []
        self._forward = []

    def add_new(self, state):
        self._backward.append(state)
        self._forward.clear()

    def pop_back(self, current_state):
        if not self._backward:
            return None
        if current_state is not None:
            self._forward.append(current_state)
        return self._backward.pop(-1)

    def pop_forward(self, current_state):
        if not self._forward:
            return None
        if current_state is not None:
            self._backward.append(current_state)
        return self._forward.pop(-1)


class LayoutManager:

    def __init__(self, resource_resolver, module_command_registry, object_registry):
        self._resource_resolver = resource_resolver
        self._module_command_registry = module_command_registry
        self._object_registry = object_registry
        self._locale = 'en'
        self._cmd_pane = self._construct_cmd_pane()
        self._dir_buttons = []
        self._element_buttons = []
        self._current_state = None
        self._current_item_observer = None
        self._history = History()

    def build_default_layout(self, app):
        text_object = TextObject('hello')
        text_view = TextView(text_object)
        self._tab_view = tab_view = TabView()
        tab_view.addTab(text_view, text_view.get_title())
        window = Window(on_closed=app.stop)
        window.setCentralWidget(tab_view)
        window.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._cmd_pane)
        # window.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._cmd_pane)
        window.menuBar().addMenu(self._build_global_menu(app, "&File"))
        window.menuBar().addMenu(self._build_navigation_menu("&Navigation"))
        window.show()
        self._window = window

    def _build_global_menu(self, app, title):
        menu = QtGui.QMenu(title)
        for command in self._module_command_registry.get_all_commands():
            resource = self._resource_resolver.resolve(command.resource_key, self._locale)
            if resource:
                text = resource.text
                shortcut_list = resource.shortcut_list
            else:
                text = command.id
                shortcut_list = None
            menu.addAction(make_async_action(menu, text, shortcut_list, self._run_command, command))
        if not menu.isEmpty():
            menu.addSeparator()
        for command in app.get_global_commands():
            menu.addAction(make_async_action(menu, command.id, [], self._run_command, command))
        return menu

    def _build_navigation_menu(self, title):
        menu = QtGui.QMenu(title)
        menu.addAction(make_async_action(menu, 'Go back', ['Escape', 'Alt+Left'], self._navigate_backward))
        menu.addAction(make_async_action(menu, 'Go forward', ['Alt+Right'], self._navigate_forward))
        return menu

    def _construct_cmd_pane(self):
        layout = QtGui.QVBoxLayout(spacing=1)
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addSpacing(10)
        widget = QtGui.QWidget()
        widget.setLayout(layout)
        pane = QtGui.QDockWidget()
        pane.setWidget(widget)
        pane.setFeatures(pane.NoDockWidgetFeatures)
        return pane

    def _update_dir_buttons(self, object):
        for button in self._dir_buttons:
            button.deleteLater()
        self._dir_buttons.clear()
        for command in object.get_command_list():
            if command.kind != 'object':
                continue
            text = command.id
            button = QtGui.QPushButton(text, focusPolicy=QtCore.Qt.NoFocus)
            button.pressed.connect(partial(asyncio.ensure_future, self._run_command(command)))
            layout = self._cmd_pane.widget().layout()
            layout.insertWidget(len(self._dir_buttons), button)  # must be inserted before spacing
            self._dir_buttons.append(button)

    def update_element_commands(self, object, current_item_key):
        _log.debug('Update element commands for item %r', current_item_key)
        for button in self._element_buttons:
            button.deleteLater()
        self._element_buttons.clear()
        for command in object.get_item_command_list(current_item_key):
            text = command.id
            button = QtGui.QPushButton(text, focusPolicy=QtCore.Qt.NoFocus)
            button.pressed.connect(partial(asyncio.ensure_future, self._run_command(command, current_item_key)))
            layout = self._cmd_pane.widget().layout()
            layout.addWidget(button)
            self._element_buttons.append(button)

    async def _run_command(self, command, *args, **kw):
        _log.info('Run command: %r', command.id)
        state = await command.run(*args, **kw)
        if state is None:
            return
        if self._current_state:
            self._history.add_new(self._current_state)
        await self._open(state)

    async def _open(self, state):
        object = await self._object_registry.resolve_async(state)
        self._current_item_observer = observer = _CurrentItemObserver(self, object)
        view = self._make_view(object, observer)
        tab_view = self._tab_view
        old_widget = tab_view.widget(0)
        tab_view.removeTab(0)
        old_widget.deleteLater()
        tab_view.insertTab(0, view, view.get_title())
        self._update_dir_buttons(object)
        self._current_state = state

    def _make_view(self, object, observer):
        if isinstance(object, ListObject):
            return self._make_list_view(object, observer)
        if isinstance(object, TreeObject):
            return self._make_tree_view(object, observer)
        assert False, repr(object)

    def _make_list_view(self, object, observer):
        sort_column_id = 'key'
        resource_key = resource_key_t(__module_ref__, [])
        list_view = ListView(self._resource_resolver, self._locale, resource_key, object)
        list_view.add_observer(observer)
        return list_view

    def _make_tree_view(self, object, observer):
        sort_column_id = 'key'
        resource_key = resource_key_t(__module_ref__, [])
        tree_view = TreeView(self._resource_resolver, self._locale, resource_key, object)
        tree_view.add_observer(observer)
        return tree_view

    async def _navigate_backward(self):
        state = self._history.pop_back(self._current_state)
        if state is not None:
            await self._open(state)

    async def _navigate_forward(self):
        state = self._history.pop_forward(self._current_state)
        if state is not None:
            await self._open(state)


class ThisModule(ClientModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME, services)
        services.layout_manager = LayoutManager(
            services.resource_resolver,
            services.module_command_registry,
            services.object_registry,
            )
