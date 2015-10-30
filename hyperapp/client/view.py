# base class for Views

import weakref
from PySide import QtCore, QtGui
from ..common.interface import tHandle
from .qt_keys import print_key_event
from .util import DEBUG_FOCUS, make_action, focused_index
from .object import ObjectObserver
from .view_command import BoundViewCommand, UnboundViewCommand
from .view_registry import view_registry


class Handle(object):

    def get_object( self ):
        raise NotImplementedError(self.__class__)

    def get_title( self ):
        return self.get_object().get_title()

    def get_module_ids( self ):
        return self.get_object().get_module_ids()

    def construct( self, parent ):
        raise NotImplementedError(self.__class__)


class View(ObjectObserver):

    CmdPanelHandleCls = None  # registered by cmd_view

    def __init__( self, parent=None ):
        ObjectObserver.__init__(self)
        self._parent = weakref.ref(parent) if parent is not None else None
        self._commands = []  # BoundViewCommand list
        self._init_commands()

    def _init_commands( self ):
        for name in dir(self):
            attr = getattr(self, name)
            if isinstance(attr, UnboundViewCommand):
                self._commands.append(attr.bind(self))

    def object_changed( self ):
        self.view_changed()

    def get_widget( self ):
        return self

    def get_current_child( self ):
        return None

    def get_current_view( self ):
        child = self.get_current_child()
        if child:
            return child.get_current_view()
        else:
            return self

    def get_commands( self ):
        commands = self._commands[:]
        view = self.get_current_child()
        if view:
            commands += view.get_commands()
        return commands

    def get_shortcut_ctx_widget( self, view ):
        return view.get_widget()

    def get_title( self ):
        view = self.get_current_child()
        if view:
            return view.get_title()
        object = self.get_object()
        if object:
            return object.get_title()
        return 'Untitled'

    def get_object( self ):
        view = self.get_current_child()
        if view:
            return view.get_object()
        else:
            return None

    def get_object_commands( self, *args, **kw ):
        child = self.get_current_child()
        if child:
            return child.get_object_commands(*args, **kw)
        object = self.get_object()
        if object:
            return [cmd.as_object_command(self) for cmd in object.get_commands(*args, **kw)]
        else:
            return []

    def run_object_command( self, command_id ):
        handle = self.get_object().run_command(command_id, self)
        if handle:  # command is handled by client-side
            self.open(handle)

    def run_object_element_command( self, command_id, element_key ):
        handle = self.get_object().run_element_command(command_id, element_key, self)
        if handle:  # command is handled by client-side
            self.open(handle)

    def get_selected_elts( self ):
        view = self.get_current_child()
        if view:
            return view.get_selected_elts()
        else:
            return None

    def selected_elements_changed( self, elts ):
        parent = self._parent()
        if parent:
            parent.selected_elements_changed(elts)

    def object_selected( self, obj ):
        return self._parent().object_selected(obj)

    def process_handle_open( self, server, result ):
        if result is None: return  # no new view opening is requested
        tHandle.validate('Handle', result)
        handle = view_registry.resolve(server, result)
        assert isinstance(handle, Handle), repr(handle)  # view_registry resolved not to a handle
        self.open(handle)

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
        child = self.get_current_child()
        if DEBUG_FOCUS: print '  * view.get_widget_to_focus', self, child
        if child:
            return child.get_widget_to_focus()
        return self.get_widget()

    def hide_current( self ):
        self._parent().hide_current()

    def print_key_event( self, evt, prefix ):
        print_key_event(evt, '%s %s %s' % (prefix, self._cls2name(self), hex(id(self))))

    def _cls2name( self, cls ):
        return cls.__module__ + '.' + cls.__class__.__name__

    def pick_arg( self, kind ):
        return self._parent().pick_arg(kind)
