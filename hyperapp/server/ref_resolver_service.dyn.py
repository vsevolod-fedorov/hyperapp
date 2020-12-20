import logging

from hyperapp.common.module import Module
from . import htypes
from .local_server_paths import LOCAL_REF_RESOLVER_REF_PATH, save_bundle_to_file

log = logging.getLogger(__name__)


REF_RESOLVER_SERVICE_ID = 'ref_resolver'

class RefResolverService(object):

    def __init__(self, ref_resolver):
        self._ref_resolver = ref_resolver

    def rpc_resolve_ref(self, request, ref):
        capsule = self._ref_resolver.resolve_ref(ref)
        if not capsule:
            raise htypes.hyper_ref.unknown_ref_error(ref)
        return request.make_response_result(capsule=capsule)


class ThisModule(Module):

    def __init__(self, module_name, services, config):
        super().__init__(module_name)
        self._ref_registry = services.ref_registry
        self._ref_resolver = services.ref_resolver
        self._service_registry = services.service_registry
        self._ref_collector_factory = services.ref_collector_factory

    # depends on mapping being generated for ref_storage
    def init_phase_3(self, services):
        iface_type_ref = services.types.reverse_resolve(htypes.hyper_ref.ref_resolver)
        service = htypes.hyper_ref.service(REF_RESOLVER_SERVICE_ID, iface_type_ref)
        service_ref = self._ref_registry.distil(service)
        self._service_registry.register(service_ref, RefResolverService, self._ref_resolver)
        ref_collector = self._ref_collector_factory()
        bundle = ref_collector.make_bundle([service_ref])
        ref_path = LOCAL_REF_RESOLVER_REF_PATH
        save_bundle_to_file(bundle, ref_path)
        log.info('Ref resolver ref is saved to %s', ref_path)

#    def init_phase_2(self, services):
#        public_key = self._server.get_public_key()
#        url = Url(RefResolver.iface, public_key, RefResolver.get_path())
#        url_with_routes = url.clone_with_routes(self._tcp_server.get_routes())
#        url_path = save_url_to_file(url_with_routes, LOCAL_REF_RESOLVER_URL_PATH)
#        log.info('Ref resolver url is saved to: %s', url_path)

#    def resolve(self, iface, path):
#        objname = path.pop_str()
#        if objname == RefResolver.class_name:
#            return RefResolver(self._server, self._ref_storage).resolve(path)
#        path.raise_not_found()
