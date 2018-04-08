import logging

from ..common.interface import hyper_ref as href_types
from ..common.ref import make_referred, make_ref
from .module import Module

log = logging.getLogger(__name__)


MODULE_NAME = 'ref_registry'


class RefRegistry(object):

    def __init__(self):
        self._registry = {}  # ref -> referred

    def register_object(self, t, object):
        referred = make_referred(t, object)
        ref = make_ref(referred)
        assert ref not in self._registry  # already registered
        self._registry[ref] = referred
        return ref

    def resolve_ref(self, ref):
        return self._registry.get(ref)


class ThisModule(Module):

    def __init__(self, services):
        super().__init__(MODULE_NAME)
        services.ref_registry = RefRegistry()
