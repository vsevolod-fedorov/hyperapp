import logging
import weakref

from PySide2 import QtCore, QtWidgets

from hyperapp.client.util import make_action, make_async_action
from hyperapp.client.command import Command, WindowCommand
from hyperapp.client.module import ClientModule
from . import htypes

log = logging.getLogger(__name__)


class MenuBar(QtWidgets.QMenuBar):

    @classmethod
    async def from_data(cls, state, command_registry, resource_resolver):
        return cls(resource_resolver, command_registry)

    def __init__(self, resource_resolver, command_registry):
        super().__init__()
        self._resource_resolver = resource_resolver
        self._build(command_registry)
        self._locale = 'en'
        command_registry.subscribe(self)

    # command registry observer method
    def commands_changed(self, kind, command_list):
        if kind == 'global':
            for command in command_list:
                self._file_menu.addAction(self._make_action(self._file_menu, command))

    def _build(self, command_registry):
        self._file_menu = self._build_global_menu('&File', command_registry)
        # self.dir_menu = QtWidgets.QMenu('&Dir')
        # self.window_menu = QtWidgets.QMenu('&Window')
        # self.help_menu = QtWidgets.QMenu('H&elp')
        # self.add_action_to_menu(self.help_menu, '&Dir commands', ['F1'], MenuBar._open_dir_commands, weakref.ref(self))
        # self.add_action_to_menu(self.help_menu, '&Current element commands', ['.'], MenuBar._open_elt_commands, weakref.ref(self))
        ## self.help_menu.setEnabled(False)
        self.addMenu(self._file_menu)
        # menu_bar.addMenu(self.dir_menu)
        # menu_bar.addMenu(self.window_menu)
        # menu_bar.addMenu(self.help_menu)

    def add_action_to_menu(self, menu, text, shortcut_list, fn, self_wr):
        menu.addAction(make_action(menu, text, shortcut_list, fn, self_wr))

    def _build_global_menu(self, title, command_registry):
        menu = QtWidgets.QMenu(title)
        # window = self.window()
        # for cmd in self._module_command_registry.get_all_commands():
        #     assert isinstance(cmd, Command), repr(cmd)
        #     window_command = WindowCommand.from_command(cmd, window)
        #     menu.addAction(self._make_action(menu, window_command))
        # if not menu.isEmpty():
        #     menu.addSeparator()
        # for cmd in self.window().get_global_commands():
        #     assert isinstance(cmd, Command), repr(cmd)
        #     menu.addAction(self._make_action(menu, cmd))
        return menu

    def _make_action(self, menu, cmd, used_shortcut_set=None):
        resource = self._resource_resolver.resolve(cmd.resource_key, self._locale)
        if resource:
            text = resource.text
            shortcut_list = resource.shortcut_list
        else:
            text = '.'.join(cmd.resource_key.path)
            shortcut_list = None
        if not cmd.is_enabled():
            shortcut_list = None
        if used_shortcut_set is not None:
            # remove duplicates
            shortcut_list = [sc for sc in shortcut_list or [] if sc not in used_shortcut_set]
            used_shortcut_set |= set(shortcut_list)
        action = make_async_action(menu, text, shortcut_list, cmd.run)
        action.setEnabled(cmd.is_enabled())
        return action

    def _current_view(self):
        return self.window().get_current_view()

    @staticmethod
    def _open_dir_commands(self_wr):
        self = self_wr()
        if self.current_dir is None: return
        assert 0  # todo
        ## self._current_view().open(cmd_view.Handle(None, [self.current_dir], take_dir_commands=True))

    @staticmethod
    def _open_elt_commands(self_wr):
        self = self_wr()
        assert 0  # todo
        ## self._current_view().open(cmd_view.Handle(None, [self.selected_elts], take_dir_commands=False))

    def view_changed(self, window):
        log.debug('-- menu_bar view_changed object=%r', window.get_object())
        self.current_dir = dir = window.get_object()
        self.help_menu.setEnabled(dir is not None)
        used_shortcut_set = set()
        self._update_dir_menu(window, used_shortcut_set)
        self._update_window_menu(window, used_shortcut_set)

    def view_commands_changed(self, window, command_kinds):
        pass

    def _update_dir_menu(self, window, used_shortcut_set):
        self.dir_menu.clear()
        command_list = window.get_command_list()
        for command in command_list:
            assert isinstance(command, Command), repr(command)
            if command.kind != 'object': continue
            #if command.is_system(): continue
            self.dir_menu.addAction(self._make_action(self.dir_menu, command, used_shortcut_set))
        self.dir_menu.setEnabled(command_list != [])

    def _update_window_menu(self, window, used_shortcut_set):
        self.window_menu.clear()
        # later commands are from deeper views
        # we must iterate in reverse order so deeper view's shortcuts override shallow ones
        last_view = None
        last_action = None
        for command in reversed(window.get_command_list()):
            assert isinstance(command, Command), repr(command)
            if command.kind != 'view': continue
            #if command.is_system(): continue
            action = self._make_action(self.window_menu, command, used_shortcut_set)
            if last_action:
                self.window_menu.insertAction(last_action, action)
            else:
                self.window_menu.addAction(action)
            if last_view and command.get_view() is not last_view:
                self.window_menu.insertSeparator(last_action)
            last_action = action
            last_view = command.get_view()

    def __del__(self):
        log.info('~menu_bar')


class ThisModule(ClientModule):

    def __init__(self, module_name, services):
        super().__init__(module_name, services)
        services.view_registry.register_type(htypes.menu_bar.menu_bar, MenuBar.from_data, services.resource_resolver)
