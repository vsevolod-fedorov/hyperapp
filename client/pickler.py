# pickle/unpickle using persistent ids for proxy objects

from cStringIO import StringIO
import cPickle as pickle
from common.util import str2path
from common.interface import iface_registry
from .proxy_registry import proxy_registry
from .server import Server
from .proxy_object import ProxyObject


class Pickler(object):

    def dumps( self, value ):
        io = StringIO()
        p = pickle.Pickler(io)
        p.persistent_id = self._persistent_id
        p.dump(value)
        return io.getvalue()

    def loads( self, data ):
        io = StringIO(data)
        up = pickle.Unpickler(io)
        up.persistent_load = self._persistent_load
        return up.load()

    def _persistent_id( self, obj ):
        if isinstance(obj, ProxyObject):
            return obj.get_persistent_id()

    def _persistent_load( self, id ):
        print '-- persistent_load', repr(id)
        proxy_id, iface_id, server_locator, path_str = id.split(' ', 3)
        iface = iface_registry.resolve(iface_id)
        server = Server.resolve_locator(server_locator)
        path = str2path(path_str)
        return proxy_registry.resolve(server, path, proxy_id, iface)


pickler = Pickler()
