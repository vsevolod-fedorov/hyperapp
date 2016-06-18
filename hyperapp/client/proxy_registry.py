# registries for proxy objects and requests

import weakref
from .objimpl_registry import objimpl_registry


# todo: remove - it was required for object unpickling, by persistent id resolver
class ProxyClassRegistry(object):

    def __init__( self ):
        self.implid2class = {}  # objimpl_id -> proxy class

    def register( self, cls ):
        objimpl_id = cls.get_objimpl_id()
        assert objimpl_id not in self.implid2class, repr(objimpl_id)  # Already registered. Duplicate?
        objimpl_registry.register(objimpl_id, cls.from_state)
        self.implid2class[objimpl_id] = cls

    def resolve( self, objimpl_id ):
        assert objimpl_id in self.implid2class, repr(objimpl_id)  # Not found
        return self.implid2class[objimpl_id]


# all proxy objects are registered in this class
# in particular, to avoid multiple proxy objects with the same url
# also used to distribute received updates (by Server class)
class ProxyRegistry(object):

    def __init__( self ):
        self.instances = weakref.WeakValueDictionary()   # (server id, path str) -> ProxyObject

    def register( self, server, path, object ):
        key = self._make_key(server, path)
        assert key not in self.instances, repr(key)  # Already registered. Duplicate?
        self.instances[key] = object

    def resolve( self, server_public_key, path ):
        key = self._make_key(server_public_key, path)
        return self.instances.get(key)

    def _make_key( self, server_public_key, path ):
        return (server_public_key.get_id(),) + tuple(path)


proxy_class_registry = ProxyClassRegistry()
proxy_registry = ProxyRegistry()
