import logging
from PySide import QtCore, QtGui

from hyperapp.common.util import is_list_inst
from hyperapp.common.htypes import tInt, TList, Field, TRecord
from hyperapp.client.util import DEBUG_FOCUS, call_after, key_match
from hyperapp.client.command import command
from hyperapp.client.module import ClientModule
from hyperapp.client.view import View
from . import htypes
from . import splitter

log = logging.getLogger(__name__)


MODULE_NAME = 'tab_view'


class TabView(QtGui.QTabWidget, View):

    @classmethod
    async def from_state(cls, locale, state, module_registry, view_registry):
        children = []
        for tab_state in state.tabs:
            child = await view_registry.resolve(locale, tab_state)
            children.append(child)
        view = cls(locale, view_registry, children, state.current_tab)
        view.init(module_registry)
        return view

    @staticmethod    
    def map_current(state, mapper):
        idx = state.current_tab
        return htypes.tab_view.tab_view_state(state.tabs[:idx] + [mapper(state.tabs[idx])] + state.tabs[idx+1:], idx)

    def __init__(self, locale, view_registry, children, current_idx):
        assert is_list_inst(children, View), repr(children)
        QtGui.QTabWidget.__init__(self)
        View.__init__(self)
        self._locale = locale
        self._view_registry = view_registry
        self.tabBar().setFocusPolicy(QtCore.Qt.NoFocus)
        self.setElideMode(QtCore.Qt.ElideMiddle)
        self._children = []  # view list
        for child in children:
            child.set_parent(self)
            self.addTab(child.get_widget(), child.get_title())
            self._children.append(child)
        self.setCurrentIndex(current_idx)
        self.currentChanged.connect(self._on_current_changed)

    def get_state(self):
        return htypes.tab_view.tab_view_state([view.get_state() for view in self._children], self.currentIndex())

    def get_current_child(self):
        idx = self.currentIndex()
        if idx == -1 or idx >= len(self._children): return None  # changing right now
        return self._children[idx]

    def view_changed(self, child):
        idx = self.currentIndex()
        if idx == -1: return  # constructing right now
        if idx >= len(self._children) or child is not self._children[idx]:
            return  # this child may be deleted right now
        w = self.widget(idx)
        if child is not self._children[idx] or w is not child.get_widget():
            if DEBUG_FOCUS: log.info('*** tab_view.view_changed: replacing tab self=%r idx=%r child=%r', self, idx, child)
            self.removeTab(idx)
            w.deleteLater()
            self.insertTab(idx, child.get_widget(), child.get_title())
            self.setCurrentIndex(idx)
            child.ensure_has_focus()
        self.setTabText(idx, child.get_title())
        View.view_changed(self)  # notify parents

    def open(self, handle):
        idx = self.currentIndex()
        self._children[idx].open(handle)

    def _on_current_changed(self, idx):
        View.view_changed(self)

    def setVisible(self, visible):
        if DEBUG_FOCUS: log.info('*** tab_view.setVisible self=%r visible=%r current-tab#=%d', self, visible, self.currentIndex())
        QtGui.QTabWidget.setVisible(self, visible)

    @command('duplicate_tab')
    async def duplicate_tab(self):
        idx = self.currentIndex()
        state = self._children[idx].get_state()
        new_view = await self._view_registry.resolve(self._locale, state, self)
        self._insert_tab(idx + 1, new_view)
        self._parent().view_changed(self)

    @command('close_tab')
    def close_tab(self):
        if len(self._children) == 1: return  # never close last tab
        idx = self.currentIndex()
        self._remove_tab(idx)
        if idx >= len(self._children):
            idx -= 1
        View.view_changed(self)  # notify parents

    @command('split_horizontally')
    async def split_horizontally(self):
        await self._map_current(splitter.split(splitter.horizontal))

    @command('split_vertically')
    async def split_vertically(self):
        await self._map_current(splitter.split(splitter.vertical))

    @command('unsplit')
    async def unsplit(self):
        await self._map_current(splitter.unsplit)

    async def _map_current(self, mapper):
        idx = self.currentIndex()
        state = mapper(self._children[idx].get_state())
        if not state: return
        self._remove_tab(idx)
        child = await self._view_registry.resolve(self._locale, state, self)
        self._insert_tab(idx, child)
        child.ensure_has_focus()
        View.view_changed(self)  # notify parents

    def _remove_tab(self, idx):
        w = self.widget(idx)
        # remove child first so later view_changed calls from child being deleted may be ignored:
        del self._children[idx]
        self.removeTab(idx)
        w.deleteLater()

    def _insert_tab(self, idx, child):
        self.insertTab(idx, child.get_widget(), child.get_title())
        self._children.insert(idx, child)
        self.setCurrentIndex(idx)

    def __del__(self):
        log.info('~tab_view')


class ThisModule(ClientModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME, services)
