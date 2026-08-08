from .services import (
    assoc_implanters,
    web,
    )


class AssocImplanter:

    def __init__(self, assoc_creg):
        self._assoc_creg = assoc_creg

    def init(self):
        assoc_implanters.append(self.hook)

    def implant(self, associations):
        for ref in associations:
            assoc, t = web.summon_with_t(ref)
            self.hook(assoc, t)

    def hook(self, assoc, t):
        self._assoc_creg.animate(assoc)


def assoc_implanter(assoc_creg):
    return AssocImplanter(assoc_creg)


def assoc_creg(config, system_code_registry_factory):
    return system_code_registry_factory('assoc_creg', config)
