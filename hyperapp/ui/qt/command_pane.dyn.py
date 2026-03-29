import asyncio
import logging
from functools import partial

from PySide6 import QtCore, QtWidgets

from . import htypes
from .code.mark import mark
from .code.view import Item, View
from .code.command import command_text

log = logging.getLogger(__name__)


class CommandPane(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.command_to_button = {}


class CommandPaneView(View):

    @classmethod
    @mark.view
    def from_piece(cls, piece, ctx, format, get_command_group, shortcut_reg):
        return cls(format, get_command_group, shortcut_reg)

    def __init__(self, format, get_command_group, shortcut_reg):
        super().__init__()
        self._format = format
        self._get_command_group = get_command_group
        self._shortcut_reg = shortcut_reg

    @property
    def piece(self):
        return htypes.command_pane.view()

    def construct_widget(self, state, ctx):
        w = CommandPane()
        layout = QtWidgets.QVBoxLayout(w, spacing=1)
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.setContentsMargins(2, 2, 2, 2)
        return w

    def widget_state(self, widget):
        return htypes.command_pane.state()

    def secondary_parent_context(self, rctx, widget):
        used_shortcuts = set()
        for button in widget.command_to_button.values():
            shortcut = button.shortcut()
            if shortcut:
                used_shortcuts.add(shortcut.toString())
        return {
            'used_shortcuts': used_shortcuts,
            }

    async def children_changed(self, ctx, rctx, widget, save_layout):
        commands = rctx.get('commands', [])
        # Postpone until upper-level views added their commands too.
        asyncio.create_task(self._update_commands(commands, widget))

    async def _update_commands(self, commands, widget):
        layout = widget.layout()
        groups = {
            cmd: self._get_command_group(cmd.key)
            for cmd in {*commands, *widget.command_to_button}
            }
        new_commands = [
            cmd for cmd in commands
            if groups[cmd] in {'model', 'context'}
            ]
        removed_commands = set(widget.command_to_button) - set(new_commands)
        new_commands = [
            cmd for cmd in new_commands
            if cmd not in set(widget.command_to_button)
            ]
        for idx in range(layout.count()):
            item = layout.itemAt(idx)
            if item and item.spacerItem():
                layout.removeItem(item)
        for cmd in removed_commands:
            button = widget.command_to_button.pop(cmd)
            button.deleteLater()
        used_shortcuts = set()
        spacer_added = False
        has_model_commands = False
        for cmd in new_commands:
            button = self._make_button(cmd, used_shortcuts)
            if groups[cmd] == 'model':
                has_model_commands = True
            elif not spacer_added and has_model_commands:
                layout.addSpacing(10)
                spacer_added = True
            layout.addWidget(button)
            widget.command_to_button[cmd] = button

    def _make_button(self, cmd, used_shortcuts):
        # text = command_text(self._format, cmd)
        text = cmd.name
        shortcut = self._shortcut_reg.get(cmd.key)
        enabled = True
        if shortcut and shortcut not in used_shortcuts:
            text += f' ({shortcut})'
        button = QtWidgets.QPushButton(
            text, focusPolicy=QtCore.Qt.NoFocus, enabled=enabled)
        button.pressed.connect(cmd.start)
        if shortcut and shortcut not in used_shortcuts:
            button.setShortcut(shortcut)
            used_shortcuts.add(shortcut)
        tooltip = cmd.name
        # if not enabled:
        #     tooltip += '\n' + cmd.disabled_reason
        button.setToolTip(tooltip)
        return button
