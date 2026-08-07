# register capsules and routes from a bundle

import logging

log = logging.getLogger(__name__)


class Unbundler:

    def __init__(self, web, mosaic, assoc_implanters):
        self._web = web
        self._mosaic = mosaic
        self._assoc_implanters = assoc_implanters

    def register_bundle(self, bundle, register_associations=True):
        ref_set = set()
        for capsule in bundle.capsule_list:
            ref_set.add(self._mosaic.register_capsule(capsule))
        if not register_associations:
            return ref_set
        # Meta associations should be registered before others. So, collect association list first.
        ass_list = []
        for ref in bundle.associations:
            decoded_capsule = self._mosaic.resolve_ref(ref)
            log.debug("Unbundle association: %s %s: %s", ref, decoded_capsule.t, decoded_capsule.value)
            for implanter in self._assoc_implanters:
                implanter(decoded_capsule.value, decoded_capsule.t)
        return ref_set | set(bundle.associations)
