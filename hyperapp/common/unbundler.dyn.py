# register capsules and routes from a bundle


import logging

from hyperapp.common.ref import LOCAL_TRANSPORT_REF
from hyperapp.common.module import Module

log = logging.getLogger(__name__)


class Unbundler(object):

    def __init__(self, mosaic, route_registry):
        self._mosaic = mosaic
        self._route_registry = route_registry

    def register_bundle(self, bundle):
        for capsule in bundle.capsule_list:
            self._mosaic.register_capsule(capsule)
        # for route in bundle.route_list:
        #     if route.transport_ref == LOCAL_TRANSPORT_REF:
        #         continue  # must be handled by transport
        #     self._route_registry.register(route)


class ThisModule(Module):

    def __init__(self, module_name, services, config):
        super().__init__(module_name)
        # route_registry = services.route_registry
        route_registry = None
        services.unbundler = Unbundler(services.mosaic, route_registry)
