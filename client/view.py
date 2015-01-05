# base class for Views

import weakref
from PySide import QtCore, QtGui
from qt_keys import print_key_event
from util import DEBUG_FOCUS, make_action, focused_index
from view_command import BoundViewCommand, UnboundViewCommand
import list_obj


class Handle(object):

    def title( self ):
        raise NotImplementedError(self.__class__)

    def construct( self, parent ):
        raise NotImplementedError(self.__class__)

    def map_current( self, mapper ):
        raise NotImplementedError(self.__class__)


class View(object):

    CmdPanelHandleCls = None  # registered by cmd_view

    def __init__( self, parent=None ):
        self._parent = weakref.ref(parent) if parent is not None else None
        self._commands = []  # BoundViewCommand list
        self._init_commands()

    def _init_commands( self ):
        for name in dir(self):
            attr = getattr(self, name)
            if isinstance(attr, UnboundViewCommand):
                self._commands.append(attr.bind(self))

    def get_widget( self ):
        return self

    def current_child( self ):
        return None

    def current_view( self ):
        child = self.current_child()
        if child:
            return child.current_view()
        else:
            return self

    def get_commands( self ):
        commands = self._commands[:]
        view = self.current_child()
        if view:
            commands += view.get_commands()
        return commands

    def get_shortcut_ctx_widget( self, view ):
        return view.get_widget()

    def title( self ):
        view = self.current_child()
        if view:
            return view.title()
        else:
            return 'Untitled'

    def current_dir( self ):
        view = self.current_child()
        if view:
            return view.current_dir()
        else:
            return None

    def selected_elts( self ):
        view = self.current_child()
        if view:
            return view.selected_elts()
        else:
            return None

    def selected_elements_changed( self, elts ):
        parent = self._parent()
        if parent:
            parent.selected_elements_changed(elts)

    def object_selected( self, obj ):
        return self._parent().object_selected(obj)

    def open( self, handle ):
        self._parent().open(handle)

    def hide_me( self ):
        self._parent().hide_current()

    def replace_view( self, mapper ):
        return mapper(self.handle())

    def get_global_commands( self ):
        return self._parent().get_global_commands()

    def view_changed( self, view=None ):
        self._parent().view_changed(self)

    def has_focus( self ):
        return focused_index(None, [self]) == 0

    def ensure_has_focus( self ):
        if DEBUG_FOCUS: print '  * view.ensure_has_focus', self
        if not self.has_focus():
            self.acquire_focus()

    def acquire_focus( self ):
        w = self.get_widget_to_focus()
        if DEBUG_FOCUS: print '*** view.acquire_focus', self, w
        assert w.focusPolicy() & QtCore.Qt.StrongFocus == QtCore.Qt.StrongFocus, (self, w, w.focusPolicy())  # implement your own get_widget_to_focus otherwise
        w.setFocus()

    def get_widget_to_focus( self ):
        child = self.current_child()
        if DEBUG_FOCUS: print '  * view.get_widget_to_focus', self, child
        if child:
            return child.get_widget_to_focus()
        return self.get_widget()

    def hide_current( self ):
        self._parent().hide_current()

    def get_arg_editor( self, obj_kind, args ):
        assert isinstance(obj_kind, ObjKind), repr(obj_kind)
        return self._parent().get_arg_editor(obj_kind, args)

    def make_action( self, title, shortcut, fn, *args, **kw ):
        make_action(self.get_widget(), title, shortcut, fn, *args, **kw)

    def print_key_event( self, evt, prefix ):
        print_key_event(evt, '%s %s %s' % (prefix, self._cls2name(self), hex(id(self))))

    def _cls2name( self, cls ):
        return cls.__module__ + '.' + cls.__class__.__name__

    def pick_arg( self, kind ):
        return self._parent().pick_arg(kind)

    def run( self, cmd, *args ):
        assert isinstance(cmd, (command, list_obj.Command)) and cmd.is_bound2inst(), repr(cmd)
        handle = self._run_handle(cmd, args)
        if handle:
            self.open(handle)

    def _run_handle( self, cmd, args ):
        if not cmd.args:
            return cmd.run(*args)
        arg0 = self.pick_arg(cmd.args[0].kind)
        if arg0 is not None:
            args = args + (arg0,)
            if len(cmd.args) == 1:
                return cmd.run(*args)
        return self.CmdPanelHandleCls(cmd, list(args))
