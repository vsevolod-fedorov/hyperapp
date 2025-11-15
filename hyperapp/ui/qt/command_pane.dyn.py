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
        self.spacing_idx = None


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
        layout.addSpacing(10)
        w.spacing_idx = 0
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
        layout = widget.layout()
        command_group = {
            cmd: self._get_command_group(cmd.key)
            for cmd in commands
            }
        new_commands = [
            cmd for cmd in commands
            if command_group[cmd] == 'context'
            ]
        removed_commands = set(widget.command_to_button) - set(new_commands)
        # widget.spacing_idx -= sum(1 for cmd in removed_commands if 'context' in cmd.groups)
        new_commands = [
            cmd for cmd in new_commands
            if cmd not in set(widget.command_to_button)
            ]
        for cmd in removed_commands:
            button = widget.command_to_button.pop(cmd)
            button.deleteLater()
        used_shortcuts = set()
        for cmd in new_commands:
            button = self._make_button(cmd, used_shortcuts)
            if False:  # pane_1_d in cmd.groups:
                layout.insertWidget(widget.spacing_idx, button)
            else:
                layout.addWidget(button)
            widget.command_to_button[cmd] = button
        # widget.spacing_idx += sum(1 for cmd in new_commands if pane_1_d in cmd.groups)

    def _make_button(self, cmd, used_shortcuts):
        # text = command_text(self._format, cmd)
        text = cmd.name
        shortcut = None  # self._shortcut_reg.get(cmd.d)
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
