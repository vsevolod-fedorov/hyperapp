from datetime import datetime
import logging
import threading
import queue

from dateutil.tz import tzlocal

from hyperapp.common.htypes import route_t
from hyperapp.common.ref import LOCAL_TRANSPORT_REF, encode_bundle, decode_bundle
from hyperapp.common.visual_rep import pprint
from hyperapp.common.module import Module
from . import htypes

log = logging.getLogger(__name__)


class PhonyServer(object):

    def __init__(self, on_failure, ref_resolver, types, route_registry, unbundler, remoting, request_queue, phony_client_address_ref):
        self._on_failure = on_failure
        self._ref_resolver = ref_resolver
        self._types = types
        self._route_registry = route_registry
        self._unbundler = unbundler
        self._remoting = remoting
        self._request_queue = request_queue
        self._phony_client_address_ref = phony_client_address_ref
        self._stop_flag = False
        self._thread = threading.Thread(target=self._thread_main)

    def start(self):
        self._thread.start()

    def stop(self):
        if self._stop_flag:
            log.info('Phony server: already stopping')
            return
        log.info('Phony server: stopping...')
        self._stop_flag = True
        self._thread.join()

    def _thread_main(self):
        log.info('Phony server is started')
        try:
            while not self._stop_flag:
                self._receive_and_process_bundle()
        except Exception as x:
            log.exception('Phony server thread is failed:')
            self._on_failure('Phony server thread is failed: %r' % x)
        log.info('Phony server is finished')

    def _receive_and_process_bundle(self):
        log.info('Phony server: picking request bundle:')
        try:
            encoded_bundle = self._request_queue.get(timeout=1)  # seconds
        except queue.Empty:
            log.info('Phony server: picking request bundle: none')
            return  # timed out, will try again
        log.info('Phony server: picking request bundle: got one:')
        bundle = decode_bundle(encoded_bundle)
        pprint(bundle, indent=1)
        self._unbundler.register_bundle(bundle)
        self._register_incoming_routes(bundle.route_list)
        for root_ref in bundle.roots:
            capsule = self._ref_resolver.resolve_ref(root_ref)
            rpc_request = self._types.decode_capsule(capsule, expected_type=htypes.hyper_ref.rpc_message).value
            assert isinstance(rpc_request, htypes.hyper_ref.rpc_request)
            self._route_registry.register(
                route_t(rpc_request.source_endpoint_ref, self._phony_client_address_ref, datetime.now(tzlocal())))
            self._remoting.process_rpc_request(root_ref, rpc_request)

    def _register_incoming_routes(self, route_list):
        for route in route_list:
            if route.transport_ref == LOCAL_TRANSPORT_REF:
                self._route_registry.register(
                    route_t(route.endpoint_ref, self._phony_client_address_ref, route.available_at))


class PhonyTransport(object):

    def __init__(self, address, ref_collector_factory, response_queue):
        self._ref_collector_factory = ref_collector_factory
        self._response_queue = response_queue

    def send(self, message_ref):
        ref_collector = self._ref_collector_factory()
        bundle = ref_collector.make_bundle([message_ref])
        encoded_bundle = encode_bundle(bundle)
        log.info('Phony server transport: enqueueing bundle...')
        self._response_queue.put(encoded_bundle)
        

class ThisModule(Module):

    def __init__(self, module_name, services, config):
        super().__init__(module_name)
        # queues are expected to be created by test
        phony_client_address_ref = services.mosaic.distil(
            htypes.phony_transport.client_address())
        phony_server_address_ref = services.mosaic.distil(
            htypes.phony_transport.server_address())
        self._server = PhonyServer(
            services.failed,
            services.ref_resolver,
            services.types,
            services.route_registry,
            services.unbundler,
            services.remoting,
            services.request_queue,
            phony_client_address_ref,
            )
        services.transport_registry.register_actor(
            htypes.phony_transport.client_address,
            PhonyTransport,
            services.ref_collector_factory,
            services.response_queue,
            )
        services.local_transport_ref_set.add(phony_server_address_ref)
        services.on_start.append(self._server.start)
        services.on_stop.append(self._server.stop)
