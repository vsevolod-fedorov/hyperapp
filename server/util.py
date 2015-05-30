import weakref
from functools import partial
from datetime import datetime
from dateutil.tz import tzutc


def utcnow():
    return datetime.now(tzutc())

def str2id( s ):
    if s == 'new':
        return None
    else:
        return int(s)

def id2str( id ):
    if id is None:
        return 'new'
    else:
        return str(id)


class _KeyedRef(weakref.ref):

    __slots__ = "key",

    def __new__( type, ob, callback, key ):
        self = weakref.ref.__new__(type, ob, callback)
        self.key = key
        return self

    def __init__(self, ob, callback, key):
        weakref.ref.__init__(self, ob, callback)


class WeakValueMultiDict(object):

    def __init__( self ):
        self.data = {}  # key -> _KeyedRef list

    def add( self, key, value ):
        l = self.data.setdefault(key, [])
        wr = _KeyedRef(value, partial(self._remove, weakref.ref(self)), key)
        l.append(wr)

    def remove( self, key, value ):
        cleaned = []
        for wr in self.data.get(key, []):
            v = wr()
            if v is not None and v != value:
                cleaned.append(wr)
        self.data[key] = cleaned
        
    def get( self, key ):
        l = []
        for wr in self.data.get(key, []):
            value = wr()
            if value is not None:
                l.append(value)
        return l
            
    @staticmethod
    def _remove( self_wr, wr ):
        self = self_wr()
        if self:
            l = self.data.get(wr.key)
            if l is None: return
            l.remove(wr)
            if not l:
                del self.data[wr.key]

