import logging

from hyperapp.common.htypes import ref_t, route_t, bundle_t
from hyperapp.common.util import is_list_inst, full_type_name_to_str
from hyperapp.common.ref import ref_repr
from hyperapp.common.module import Module
from .visitor import Visitor
from . import htypes

log = logging.getLogger(__name__)


MODULE_NAME = 'ref_collector'
RECURSION_LIMIT = 100


class RefCollector(Visitor):

    def __init__(self, ref_resolver, type_resolver, route_resolver):
        self._ref_resolver = ref_resolver
        self._type_resolver = type_resolver
        self._route_resolver = route_resolver
        self._collected_ref_set = None
        self._collected_route_set = set()

    def make_bundle(self, ref_list):
        assert is_list_inst(ref_list, ref_t), repr(ref_list)
        capsule_list = self._collect_capsule_list(ref_list)
        return bundle_t(
            roots=ref_list,
            capsule_list=capsule_list,
            route_list=list(self._collected_route_set),
            )

    def _collect_capsule_list(self, ref_list):
        capsule_set = set()
        missing_ref_count = 0
        ref_set = set(ref_list)
        for i in range(RECURSION_LIMIT):
            new_ref_set = set()
            for ref in ref_set:
                capsule = self._ref_resolver.resolve_ref(ref)
                if not capsule:
                    missing_ref_count += 1
                    continue
                capsule_set.add(capsule)
                new_ref_set |= self._collect_refs_from_capsule(ref, capsule)
            if not new_ref_set:
                break
            ref_set = new_ref_set
        else:
            assert False, 'Reached recursion limit %d while resolving refs' % RECURSION_LIMIT
        if missing_ref_count:
            log.warning('Failed to resolve %d refs', missing_ref_count)
        return list(capsule_set)

    def _collect_refs_from_capsule(self, ref, capsule):
        t = self._types.resolve(capsule.full_type_name)
        object = self._type_resolver.decode_object(t, capsule)
        log.debug('Collecting refs from %r:', object)
        self._collected_ref_set = set()
        self._collect_refs_from_object(t, object)
        # can't move following to _collect_refs_from_object because not all objects has refs to them, but for endpoint it's required
        if full_type_name_to_str(t.full_name) in ['hyper_ref.endpoint', 'hyper_ref.service']:
            self._handle_endpoint_ref(ref)
        log.info('Collected %d refs from %s %s: %s',
                      len(self._collected_ref_set),
                     full_type_name_to_str(t.full_name),
                     ref_repr(ref),
                     ', '.join(map(ref_repr, self._collected_ref_set)))
        return self._collected_ref_set

    def _collect_refs_from_object(self, t, object):
        self.visit(t, object)
        if full_type_name_to_str(t.full_name) == 'hyper_ref.rpc_message':
            self._handle_rpc_message(object)

    def visit_record(self, t, value):
        if t == ref_t:
            self._collected_ref_set.add(value)

    def _handle_endpoint_ref(self, endpoint_ref):
        transport_ref_set = self._route_resolver.resolve(endpoint_ref)
        for transport_ref in transport_ref_set:
            self._collected_route_set.add(route_t(
                endpoint_ref=endpoint_ref,
                transport_ref=transport_ref,
                ))
            self._collected_ref_set.add(transport_ref)

    def _handle_rpc_message(self, rpc_message):
        if isinstance(rpc_message, htypes.hyper_ref.rpc_request):
            self._handle_rpc_request(rpc_message)

    def _handle_rpc_request(self, rpc_request):
        iface = self._types.resolve(rpc_request.iface_full_type_name)
        command = iface[rpc_request.command_id]
        params = rpc_request.params.decode(command.request)
        self._collect_refs_from_object(command.request, params)


class ThisModule(Module):

    def __init__(self, services):
        super().__init__(MODULE_NAME)
        self._ref_resolver = services.ref_resolver
        self._type_resolver = services.type_resolver
        self._route_resolver = services.route_resolver
        services.ref_collector_factory = self._ref_collector_factory

    def _ref_collector_factory(self):
        return RefCollector(self._ref_resolver, self._type_resolver, self._route_resolver)
