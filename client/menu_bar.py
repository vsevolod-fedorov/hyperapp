import weakref
from PySide import QtCore, QtGui
from util import make_action
from command import command, get_dir_commands
#import key_binding
#import cmd_view


class MenuBar(object):

    def __init__( self, window ):
        self.window = window  # weakref.ref
        self.current_dir = None
        self.selected_elts = []
        self._build()

    def _build( self ):
        self.file_menu = self._build_global_menu('&File')
        self.dir_menu = QtGui.QMenu('&Dir')
        self.window_menu = QtGui.QMenu('W&indow')
        self.help_menu = QtGui.QMenu('H&elp')
        self.help_menu.addAction(make_action(self.window(), '&Dir commands', 'F1', self._open_dir_commands))
        self.help_menu.addAction(make_action(self.window(), '&Current element commands', '.', self._open_elt_commands))
        self.help_menu.setEnabled(False)
        menu_bar = self.window().menuBar()
        menu_bar.addMenu(self.file_menu)
        menu_bar.addMenu(self.dir_menu)
        menu_bar.addMenu(self.window_menu)
        menu_bar.addMenu(self.help_menu)

    def _build_global_menu( self, title ):
        menu = QtGui.QMenu(title)
        self._add_actions(menu, [(cmd, ()) for cmd in self.window().global_commands()])
        return menu

    def _current_view( self ):
        return self.window().current_view()

    def _make_cmd_action( self, cmd, *args ):
        ## shortcut = key_binding.get_shortcut(cmd)
        shortcut = cmd.shortcut
        return cmd.make_action(self.window(), weakref.ref(self._current_view()), shortcut, *args)

    def _add_actions( self, menu, elements ):
        for cmd, args in elements:
            menu.addAction(self._make_cmd_action(cmd, *args))

    def _open_dir_commands( self ):
        if self.current_dir is None: return
        self._current_view().open(cmd_view.Handle(None, [self.current_dir], take_dir_commands=True))

    def _open_elt_commands( self ):
        if not self.selected_elts: return
        self._current_view().open(cmd_view.Handle(None, [self.selected_elts], take_dir_commands=False))

    def view_changed( self, window ):
        self.current_dir = dir = window.current_dir()
        self.help_menu.setEnabled(dir is not None)
        self.dir_menu.clear()
        if dir is not None:
            elements = [(cmd, self._dir_cmd_args(cmd, dir)) for cmd in get_dir_commands(dir)]
            self._add_actions(self.dir_menu, elements)
            self.dir_menu.setEnabled(elements != [])
        else:
            self.dir_menu.setEnabled(False)
        self._update_window_menu(window)

    # add explicit 'dir' argument for commands which are module methods
    def _dir_cmd_args( self, cmd, dir ):
        ## if cmd.require_explicit_elt_arg():
        ##     return (dir,)
        ## else:
        ##     return ()
        return (dir,)

    def _update_window_menu( self, window ):
        self.window_menu.clear()
        last_view = None
        for cmd in window.commands():
            if last_view is not None and cmd.inst() is not last_view:
                self.window_menu.addSeparator()
            self.window_menu.addAction(self._make_cmd_action(cmd))
            last_view = cmd.inst()

    def selected_elements_changed( self, elts ):
        self.selected_elts = elts
