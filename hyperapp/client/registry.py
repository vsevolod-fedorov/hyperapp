import logging

log = logging.getLogger(__name__)


class Registry(object):

    class _Rec(object):

        def __init__(self, dynamic_module_id, factory, args, kw):
            self.dynamic_module_id = dynamic_module_id
            self.factory = factory  # factory functon
            self.args = args
            self.kw = kw

    def __init__(self):
        self._registry = {}  # id -> _Rec

    def register(self, id, factory, *args, **kw):
        self.register_provided_by_dynamic_module(None, id, factory, *args, **kw)

    def register_provided_by_dynamic_module(self, dynamic_module_id, id, factory, *args, **kw):
        log.info('registering %r from module %r to %r(%r, %r)', id, dynamic_module_id, factory, args, kw)
        assert id not in self._registry, repr(id)  # Duplicate id
        self._registry[id] = self._Rec(dynamic_module_id, factory, args, kw)

    def is_registered(self, id):
        return id in self._registry

    def get_dynamic_module_id(self, id):
        rec = self._resolve(id)
        return rec.dynamic_module_id

    def _resolve(self, id):
        assert id in self._registry, repr(id)  # Unknown id
        return self._registry[id]


class DynamicModuleRegistryProxy(object):

    def __init__(self, registry, dynamic_module_id):
        assert isinstance(registry, Registry), repr(registry)
        self._registry = registry
        self._dynamic_module_id = dynamic_module_id

    def register(self, id, factory, *args, **kw):
        self._registry.register_provided_by_dynamic_module(self._dynamic_module_id, id, factory, *args, **kw)
