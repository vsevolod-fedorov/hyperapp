# panel with commands for current dir and selected elements

import logging
import asyncio
import weakref

from PySide2 import QtCore, QtWidgets

from hyperapp.client.module import ClientModule

from . import htypes
from .layout import GlobalLayout

log = logging.getLogger(__name__)


class CommandPaneLayout(GlobalLayout):

    def __init__(self, state, path, command_hub, view_opener, resource_resolver):
        super().__init__(path)
        self._resource_resolver = resource_resolver
        self._command_hub = command_hub

    @property
    def data(self):
        return htypes.command_pane.command_pane()

    async def create_view(self):
        return CommandPane(self._resource_resolver, self._command_hub)

    async def visual_item(self):
        return self.make_visual_item('CommandPane')


class CommandPane(QtWidgets.QDockWidget):

    def __init__(self, resource_resolver, command_hub):
        QtWidgets.QDockWidget.__init__(self, 'Commands')
        self.setFeatures(self.NoDockWidgetFeatures)
        self._resource_resolver = resource_resolver
        self._locale = 'en'
        self._layout = QtWidgets.QVBoxLayout(spacing=1)
        self._layout.setAlignment(QtCore.Qt.AlignTop)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.addSpacing(10)
        self.setWidget(QtWidgets.QWidget())
        self.widget().setLayout(self._layout)
        self._dir_buttons = []
        self._element_buttons = []
        command_hub.subscribe(self)

    # command hum observer method
    def commands_changed(self, kind, command_list):
        if kind == 'object':
            self._update_dir_commands(command_list)
        if kind == 'element':
            self._update_element_commands(command_list)

    def _update_dir_commands(self, command_list):
        for button in self._dir_buttons:
            button.deleteLater()
        self._dir_buttons.clear()
        idx = 0
        for command in command_list:
            if command.kind != 'object':
                continue
            button = self._make_button(command)
            self._layout.insertWidget(idx, button)  # must be inserted before spacing
            self._dir_buttons.append(button)
            idx += 1

    def _update_element_commands(self, command_list):
        for button in self._element_buttons:
            button.deleteLater()
        self._element_buttons.clear()
        for command in command_list:
            button = self._make_button(command, set_shortcuts=True)
            self._layout.addWidget(button)
            self._element_buttons.append(button)

    def _make_button(self, command, set_shortcuts=False):
        if command.resource_key:
            resource = self._resource_resolver.resolve(command.resource_key, self._locale)
        else:
            resource = None
        if resource:
            if resource.shortcut_list:
                text = '%s (%s)' % (resource.text, resource.shortcut_list[0])
            else:
                text = resource.text
            description = resource.description
        else:
            text = command.id
            if command.resource_key:
                description = '.'.join(command.resource_key.path)
            else:
                description = None
        button = QtWidgets.QPushButton(text, focusPolicy=QtCore.Qt.NoFocus)
        button.setToolTip(description)
        button.setEnabled(command.is_enabled())
        button.pressed.connect(lambda command=command: asyncio.ensure_future(command.run()))
        if set_shortcuts and resource:
            if resource.shortcut_list:
                button.setShortcut(resource.shortcut_list[0])
            if resource.is_default:
                button.setShortcut('Return')
        return button

    # def __del__(self):
    #     log.info('~command_pane')


class ThisModule(ClientModule):

    def __init__(self, module_name, services, config):
        super().__init__(module_name, services)
        services.view_registry.register_actor(
            htypes.command_pane.command_pane, CommandPaneLayout, services.resource_resolver)
