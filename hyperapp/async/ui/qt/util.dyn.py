import asyncio
import logging
import pickle
import weakref
from datetime import datetime
from io import StringIO

from dateutil.tz import tzutc
from PySide2 import QtCore, QtWidgets

from hyperapp.common.util import is_iterable_inst

log = logging.getLogger(__name__)


DEBUG_FOCUS = False
DEBUG_EVENTS = False


class Thread(QtCore.QThread):

    # we must keep refs to running threads
    _threads = set()

    def __init__(self, target, tearDowns):
        QtCore.QThread.__init__(self)
        self._target    = target     # (fn, args, kw) tuple
        self._tearDowns = tearDowns  # (fn, args, kw) tuple list
        self._threads.add(self)

    def run(self):
        fn, args, kw = self._target
        try:
            fn(*args, **kw)
        finally:
            for fn, args, kw in self._tearDowns:
                fn(*args, **kw)
            invoke_in_main_thread(self._threads.remove, self)


def start_thread(fn, *args, **kw):
    thread = Thread((fn, args, kw), [])
    thread.start(QtCore.QThread.LowPriority)


# invoke_in_main_thread from:    
# http://stackoverflow.com/questions/10991991/pyside-easier-way-of-updating-gui-from-another-thread

class InvokeEvent(QtCore.QEvent):
    EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, fn, *args, **kwargs):
        QtCore.QEvent.__init__(self, InvokeEvent.EVENT_TYPE)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class Invoker(QtCore.QObject):
    def event(self, event):
        event.fn(*event.args, **event.kwargs)
        return True


_invoker = Invoker()

def invoke_in_main_thread(fn, *args, **kwargs):
    QtCore.QCoreApplication.postEvent(_invoker,
        InvokeEvent(fn, *args, **kwargs))

def call_after(fn, *args, **kw):
    ## print 'call_after', fn, args, kw
    QtCore.QTimer.singleShot(0, lambda: fn(*args, **kw))

def call_after_2(fn, *args, **kw):
    call_after(call_after, fn, *args, **kw)

def call_in_future(time_ms, fn, *args, **kw):
    ## print 'call_in_future', time_ms, fn, args, kw
    QtCore.QTimer.singleShot(time_ms, lambda: fn(*args, **kw))

def uni2str(v):
    if isinstance(v, str):
        return v.encode('utf-8')
    else:
        return v

def utcnow():
    return datetime.now(tzutc())

def key_match(evt, key_str):
    tokens = key_str.split('+')
    mods = tokens[:-1]
    key = getattr(QtCore.Qt, 'Key_' + tokens[-1], None)
    assert key, 'Invalid key: %r' % tokens[-1]
    for mod in mods:
        assert mod in ['Shift', 'Ctrl', 'Alt'], 'Invalid modifier: %r' % mod
    ## print '*** key_match', evt.key() == key if evt.type() == QtCore.QEvent.Type.KeyPress else '-' 
    if evt.type() != QtCore.QEvent.Type.KeyPress or evt.key() != key:
        return False
    for mod_id, mod_name in [
        (QtCore.Qt.ShiftModifier, 'Shift'),
        (QtCore.Qt.ControlModifier, 'Ctrl'),
        (QtCore.Qt.AltModifier, 'Alt'),
        ]:
        if (mod_name in mods) ^ bool(evt.modifiers() & mod_id):
            ## print '** no mod:', mod_name, mod_id, bool(evt.modifiers() & mod_id), mod_name in mods
            return False
    return True

def key_match_any(evt, keys):
    for key in keys:
        if key_match(evt, key):
            return True
    return False

def make_async_action(widget, text, shortcut_list, fn, *args, **kw):
    assert isinstance(text, str), repr(text)
    assert shortcut_list is None or is_iterable_inst(shortcut_list, str), repr(shortcut_list)
    assert callable(fn), repr(fn)
    def run():
        log.info('async action run %r %r(%s, %s)', text, fn, args, kw)
        asyncio.ensure_future(fn(*args, **kw))
    return make_action(widget, text, shortcut_list, run)

def make_action(widget, text, shortcut_list, fn, *args, **kw):
    assert isinstance(text, str), repr(text)
    assert shortcut_list is None or is_iterable_inst(shortcut_list, str), repr(shortcut_list)
    assert callable(fn), repr(fn)
    ## print '--- make_action', widget, text, shortcut_list, fn, args, kw
    def run():
        log.info('--- make_action/run widget=%r text=%r shortcut_list=%r fn=%r args=%r kw=%r', widget, text, shortcut_list, fn, args, kw)
        return fn(*args, **kw)
    action = QtWidgets.QAction(text, widget)
    action.setShortcuts(shortcut_list or [])
    action.triggered.connect(run)
    return action

def focused_index(parent, children, default=None):
    if parent:
        w = parent.focusWidget()
    else:
        w = QtWidgets.QApplication.focusWidget()
    while w:
        for idx, trg in enumerate(children):
            if w is trg: return idx
        w = w.parent()
    return default
    
