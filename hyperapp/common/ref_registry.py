# reference registry: map refs to capsules

import logging

from .htypes import capsule_t
from .htypes.deduce_value_type import deduce_value_type
from .ref import ref_repr, make_ref
from .visual_rep import pprint

log = logging.getLogger(__name__)


class RefRegistry(object):

    def __init__(self, type_resolver):
        self._type_resolver = type_resolver
        self._registry = {}  # ref -> capsule

    def register_capsule(self, capsule):
        assert isinstance(capsule, capsule_t), repr(capsule)
        ref = make_ref(capsule)
        log.info('Registering ref %s for capsule of type %s', ref_repr(ref), ref_repr(capsule.type_ref))
        existing_capsule = self._registry.get(ref)
        if existing_capsule:
            log.debug('  (already exists)')
            assert capsule == existing_capsule, repr((existing_capsule, capsule))  # new capsule does not match existing one
        self._registry[ref] = capsule
        pprint(self._type_resolver.decode_capsule(capsule).value, indent=1, logger=log.debug)
        return ref

    def register_object(self, object, t=None):
        capsule, ref = self.register_object_to_capsule_and_ref(object, t)
        return ref

    def register_object_to_capsule_and_ref(self, object, t=None):
        t = t or deduce_value_type(object)
        log.debug('Registering ref for object %s', t.name)
        capsule = self._type_resolver.make_capsule(object, t)
        ref = self.register_capsule(capsule)
        log.debug('  -> registered ref %s for object %s', ref_repr(ref), t.name)
        return (capsule, ref)

    def resolve_ref(self, ref):
        return self._registry.get(ref)
