import logging

from .ref import ref_repr

_log = logging.getLogger(__name__)


class RefResolver(object):

    def __init__(self):
        self._sources = []

    def add_source(self, source):
        self._sources.append(source)

    def resolve_ref(self, ref):
        _log.debug('Resolving ref: %s', ref_repr(ref))
        for source in self._sources:
            capsule = source.resolve_ref(ref)
            if capsule:
                _log.info('Ref %s is resolved to capsule, type %s', ref_repr(ref), ref_repr(capsule.type_ref))
                return capsule
        _log.warning('Ref %s is failed to be resolved', ref_repr(ref))
        return None
