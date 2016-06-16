# navigator component - container keeping navigation history and allowing go backward and forward

import logging
import asyncio
from PySide import QtCore, QtGui
from ..common.util import is_list_inst
from ..common.htypes import tInt, tString, TList, Field, TRecord, tHandle, tViewHandle, list_handle_type
from .util import key_match, key_match_any
from .view_registry import view_registry
from .view_command import command
from . import view
from . import composite
from . import list_view
from .history_list import HistoryRow, HistoryList

log = logging.getLogger(__name__)


MAX_HISTORY_SIZE = 100


item_type = TRecord([
    Field('title', tString),
    Field('handle', tHandle),
    ])

state_type = TRecord([
    Field('history', TList(item_type)),
    Field('current_pos', tInt),
    ])


    ## def _collect_required_module_ids( self ):
    ##     module_ids = set(composite.Handle.get_module_ids(self))
    ##     for item in self.backward_history + self.forward_history:
    ##         module_ids.update(set(item.required_module_ids))
    ##     return list(module_ids)


class View(composite.Composite):

    history_handle_type = list_handle_type('navigator_history', tInt)

    @classmethod
    def from_state( cls, parent, state ):
        child = view_registry.resolve(parent, state.history[state.current_pos].handle)
        return cls(parent, child, state.history[:state.current_pos], state.history[state.current_pos + 1:])

    def __init__( self, parent, child, backward_history=None, forward_history=None ):
        assert isinstance(child, view.View), repr(child)
        assert backward_history is None or is_list_inst(backward_history, item_type), repr(backward_history)
        assert forward_history is None or is_list_inst(forward_history, item_type), repr(forward_history)
        composite.Composite.__init__(self, parent)
        self._backward_history = backward_history or []     # item_type list
        self._forward_history = forward_history or []   # item_type list
        self._child = child

    def get_state( self ):
        history = self._backward_history \
           + [item_type(self._child.get_title(), self._child.get_state())] \
           + self._forward_history
        return state_type(history, current_pos=len(self._backward_history))

    def get_widget( self ):
        if self._child is None: return None  # constructing right now
        return self._child.get_widget()

    def set_child( self, handle ):
        #print 'history open', self._backward_history, self._forward_history, handle
        self._forward_history = []
        self._add2history(self._backward_history, self._child)
        if len(self._backward_history) > MAX_HISTORY_SIZE:
            self._backward_history = self._backward_history[-MAX_HISTORY_SIZE:]
        self._open(handle)

    def get_current_child( self ):
        return self._child

    def open( self, handle ):
        self.set_child(handle)

    def hide_current( self ):
        self._go_back()

    def _open( self, handle ):
        self._child = view_registry.resolve(self, handle)
        self._parent().view_changed(self)
        object = self._child.get_object()
        if object:
            asyncio.async(object.server_subscribe())

    @command('Go back', 'Go backward to previous page', ['Escape', 'Alt+Left'])
    def go_back( self ):
        log.info('   history back len(back_history)=%r len(forward_history)=%r', len(self._backward_history), len(self._forward_history))
        self._go_back()

    def _go_back( self ):
        if not self._backward_history:
            return False
        self._add2history(self._forward_history, self._child)
        self._open(self._pop_history(self._backward_history))

    @command('Go forward', 'Go forward to next page', 'Alt+Right')
    def go_forward( self ):
        log.info('   history forward len(back_history)=%r len(forward_history)=%r', len(self._backward_history), len(self._forward_history))
        if not self._forward_history:
            return False
        self._add2history(self._backward_history, self._child)
        self._open(self._pop_history(self._forward_history))

    def _add2history( self, history, view ):
        if isinstance(view, list_view.View) and isinstance(view.get_object(), HistoryList):
            return  # do not add history list itself to history
        history.append(item_type(view.get_title(), view.get_state()))

    def _pop_history( self, history ):
        item = history.pop()
        return item.handle

    @command('History', 'Open history', 'Ctrl+H')
    def open_history( self ):
        idx = len(self._backward_history)
        current_handle = self._child.handle()
        items = self._backward_history + [Item.from_handle(current_handle)] + list(reversed(self._forward_history))
        rows = [HistoryRow(idx, item) for idx, item in enumerate(items)]
        object = HistoryList(rows)
        self.open(list_view.Handle(self.history_handle_type, object, sort_column_id='idx', key=idx))

    def __del__( self ):
        log.info('~navigator')


view_registry.register('navigator', View.from_state)
