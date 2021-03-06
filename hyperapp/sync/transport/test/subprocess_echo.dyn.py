from hyperapp.common.htypes import bundle_t
from hyperapp.common.htypes.packet_coders import packet_coders
from hyperapp.common.module import Module


class Endpoint:

    def __init__(self, mosaic, transport, my_identity):
        self._mosaic = mosaic
        self._transport = transport
        self._my_identity = my_identity

    def process(self, request):
        my_peer_ref = self._mosaic.put(request.receiver_identity.peer.piece)
        self._transport.send(request.sender, self._my_identity, [*request.ref_list, my_peer_ref])


class ThisModule(Module):

    def __init__(self, module_name, services, config):
        super().__init__(module_name)

        master_peer_bundle = packet_coders.decode('cdr', config['master_peer_bundle_cdr'], bundle_t)
        services.unbundler.register_bundle(master_peer_bundle)
        master_peer_ref = master_peer_bundle.roots[0]
        master_peer = services.peer_registry.invite(master_peer_ref)

        my_identity = services.generate_rsa_identity(fast=True)
        my_peer_ref = services.mosaic.put(my_identity.peer.piece)

        endpoint = Endpoint(services.mosaic, services.transport, my_identity)
        services.endpoint_registry.register(my_identity, endpoint)

        ref_collector = services.ref_collector_factory()
        bundle = ref_collector.make_bundle([my_peer_ref])
        parcel = master_peer.make_parcel(bundle, my_identity)

        services.transport.send_parcel(parcel)
