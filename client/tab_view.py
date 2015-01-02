from PySide import QtCore, QtGui
from util import DEBUG_FOCUS, call_after, key_match
from command import command_owner_meta_class, command
import view
import splitter


class Handle(view.Handle):

    def __init__( self, children, current_idx=0 ):
        view.Handle.__init__(self)
        self.children = children  # handle list
        self.current_idx = current_idx  # child index, 0..

    def construct( self, parent ):
        print 'tab_view construct', parent, len(self.children), self.current_idx
        return View(parent, self.children, self.current_idx)

    def map_current( self, mapper ):
        idx = self.current_idx
        return Handle(self.children[:idx] + [mapper(self.children[idx])] + self.children[idx+1:], idx)


class View(QtGui.QTabWidget, view.View):

    __metaclass__ = command_owner_meta_class

    def __init__( self, parent, children, current_idx ):
        QtGui.QTabWidget.__init__(self)
        view.View.__init__(self, parent)
        self.tabBar().setFocusPolicy(QtCore.Qt.NoFocus)
        self.setElideMode(QtCore.Qt.ElideMiddle)
        self._children = []  # view list
        for handle in children:
            v = handle.construct(self)
            self.addTab(v.get_widget(), v.title())
            self._children.append(v)
        self.setCurrentIndex(current_idx)
        self.currentChanged.connect(self._on_current_changed)

    def handle( self ):
        return Handle([view.handle() for view in self._children], self.currentIndex())

    def current_child( self ):
        idx = self.currentIndex()
        if idx == -1 or idx >= len(self._children): return None  # changing right now
        return self._children[idx]

    def view_changed( self, child ):
        idx = self.currentIndex()
        if idx == -1: return  # constructing right now
        if idx >= len(self._children) or child is not self._children[idx]:
            return  # this child may be deleted right now
        w = self.widget(idx)
        if child is not self._children[idx] or w is not child.get_widget():
            if DEBUG_FOCUS: print '*** tab_view.view_changed: replacing tab', self, idx, child
            self.removeTab(idx)
            w.deleteLater()
            self.insertTab(idx, child.get_widget(), child.title())
            self.setCurrentIndex(idx)
            child.ensure_has_focus()
        self.setTabText(idx, child.title())
        view.View.view_changed(self)  # notify parents

    def open( self, handle ):
        # here we assume that child is a navigator view
        idx = self.currentIndex()
        self._children[idx].open(handle)  # handle it to navigator

    def _on_current_changed( self, idx ):
        view.View.view_changed(self)

    def setVisible( self, visible ):
        if DEBUG_FOCUS: print '*** tab_view.setVisible', self, visible, '(current tab#%d)' % self.currentIndex()
        QtGui.QTabWidget.setVisible(self, visible)

    @command('Ctrl+T', 'Duplicate tab')
    def duplicate_tab( self ):
        idx = self.currentIndex()
        view = self._children[idx]
        new_view = view.handle().construct(self)
        self._insert_tab(idx + 1, new_view)
        self._parent().view_changed(self)

    @command('Ctrl+F4', 'Close tab')
    def close_tab( self ):
        if len(self._children) == 1: return  # never close last tab
        idx = self.currentIndex()
        self._remove_tab(idx)
        if idx >= len(self._children):
            idx -= 1
        view.View.view_changed(self)  # notify parents

    @command('Alt+S', '&Split horizontally')
    def split_horizontally( self ):
        self._map_current(splitter.split(splitter.horizontal))

    @command('Shift+Alt+S', 'Split &vertically')
    def split_vertically( self ):
        self._map_current(splitter.split(splitter.vertical))

    @command('Alt+U', '&Unsplit')
    def unsplit( self ):
        self._map_current(splitter.unsplit)

    def _map_current( self, mapper ):
        idx = self.currentIndex()
        handle = mapper(self._children[idx].handle())
        if not handle: return
        self._remove_tab(idx)
        child = handle.construct(self)
        self._insert_tab(idx, child)
        child.ensure_has_focus()
        view.View.view_changed(self)  # notify parents

    def _remove_tab( self, idx ):
        w = self.widget(idx)
        # remove child first so later view_changed calls from child being deleted may be ignored:
        del self._children[idx]
        self.removeTab(idx)
        w.deleteLater()

    def _insert_tab( self, idx, child ):
        self.insertTab(idx, child.get_widget(), child.title())
        self._children.insert(idx, child)
        self.setCurrentIndex(idx)
