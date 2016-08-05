import os
import logging
import unittest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from hyperapp.common.htypes import (
    tString,
    Field,
    tAuxInfo,
    tPacket,
    RequestCmd,
    Interface,
    tClientPacket,
    tServerPacket,
    tRequest,
    tClientNotification,
    IfaceRegistry,
#    register_iface,
    )
from hyperapp.common.transport_packet import tTransportPacket
from hyperapp.common.identity import Identity, PublicKey
from hyperapp.common.encrypted_packet import (
    tEncryptedPacket,
    tSubsequentEncryptedPacket,
    tPopChallengePacket,
    tPopRecord,
    tProofOfPossessionPacket,
    make_session_key,
    encrypt_initial_packet,
    decrypt_packet,
    )
from hyperapp.common.packet_coders import packet_coders
from hyperapp.common.visual_rep import pprint
from hyperapp.common.route_storage import RouteStorage
from hyperapp.server.module import Module
from hyperapp.server import route_storage
from hyperapp.server.request import NotAuthorizedError, PeerChannel, Peer, RequestBase
from hyperapp.server.code_repository import CodeRepository
from hyperapp.server.remoting import Remoting
from hyperapp.server import tcp_transport
from hyperapp.server import encrypted_transport
import hyperapp.server.module as module_mod
from hyperapp.server.object import Object, subscription
from hyperapp.server.server import Server
from hyperapp.server.transport_session import TransportSession, TransportSessionList
from hyperapp.common.test.util import PhonyRouteRepository

log = logging.getLogger(__name__)


logging.basicConfig(level=logging.DEBUG, format='%(asctime)-15s  %(message)s')


test_iface = Interface('test_iface', commands=[
    RequestCmd('echo', [Field('test_param', tString)], [Field('test_result', tString)]),
    RequestCmd('required_auth', result_fields=[Field('test_result', tString)]),
    RequestCmd('broadcast', [Field('message', tString)]),
    ],
    diff_type=tString)


authorized_peer_identity = Identity.generate(fast=True)


class TestObject(Object):

    class_name = 'test_object'
    iface = test_iface

    def __init__( self, module, id ):
        Object.__init__(self)
        self.module = module
        self.id = id

    def get_path( self ):
        return self.module.make_path(self.class_name, self.id)

    def process_request( self, request ):
        if request.command_id == 'echo':
            return self.run_command_echo(request)
        if request.command_id == 'broadcast':
            return self.run_command_broadcast(request)
        if request.command_id == 'required_auth':
            return self.run_command_required_auth(request)
        return Object.process_request(self, request)

    def run_command_echo( self, request ):
        return request.make_response_result(test_result=request.params.test_param + ' to you too')

    def run_command_required_auth( self, request ):
        pk = authorized_peer_identity.get_public_key()
        if pk not in request.peer.public_keys:
            raise NotAuthorizedError(pk)
        return request.make_response_result(test_result='ok')

    def run_command_broadcast( self, request ):
        subscription.distribute_update(self.iface, self.get_path(), request.params.message)


class TestModule(module_mod.Module):

    name = 'test_module'

    def __init__( self ):
        module_mod.Module.__init__(self, self.name)

    def resolve( self, iface, path ):
        objname = path.pop_str()
        if objname == TestObject.class_name:
            obj_id = path.pop_str()
            return TestObject(self, obj_id)
        path.raise_not_found()

        
class PhonyChannel(PeerChannel):

    def send_update( self ):
        pass

    def pop_updates( self ):
        return None


class PhonyResourcesLoader(object):

    def load_resources( self, resource_id ):
        return []


class PhonyModuleRepository(object):
    pass


class TestSession(TransportSession):

    def pull_notification_transport_packets( self ):
        return []


class Services(object):

    def __init__( self ):
        self.iface_registry = IfaceRegistry()
        self.route_storage = RouteStorage(PhonyRouteRepository())
        self.resources_loader = PhonyResourcesLoader()
        self.module_repository = PhonyModuleRepository()
        self.code_repository = CodeRepository(self.module_repository, self.resources_loader)
        self.remoting = Remoting(self.iface_registry)
        self._register_transports()
        
    def _register_transports( self ):
        for module in [tcp_transport, encrypted_transport]:
            module.register_transports(self.remoting.transport_registry, self)


server_identity = Identity.generate(fast=True)


class ServerTest(unittest.TestCase):

    def setUp( self ):
        self.services = Services()
        self.iface_registry = self.services.iface_registry
        self.iface_registry.register(test_iface)
        self.remoting = self.services.remoting
        self.test_module = TestModule()  # self-registering
        self.server = Server(server_identity)
        self.session_list = TransportSessionList()

    def test_simple_request( self ):
        request_data = tRequest(
            iface='test_iface',
            path=[TestModule.name, TestObject.class_name, '1'],
            command_id='echo',
            params=test_iface.get_request_params_type('echo')(test_param='hello'),
            request_id='001',
            )
        pprint(tClientPacket, request_data)
        request = RequestBase.from_data(None, Peer(PhonyChannel()), self.iface_registry, request_data)

        response = self.server.process_request(request)

        pprint(tServerPacket, response.to_data())
        self.assertEqual('hello to you too', response.result.test_result)

    def transport_id2encoding( self, transport_id ):
        if transport_id in ['tcp.cdr', 'tcp.json']:
            return transport_id.split('.')[1]
        else:
            return 'cdr'

    def encode_packet( self, transport_id, rec, type ):
        return packet_coders.encode(self.transport_id2encoding(transport_id), rec, type)

    def decode_packet( self, transport_id, data, type ):
        return packet_coders.decode(self.transport_id2encoding(transport_id), data, type)

    def encrypt_packet( self, session_list, transport_id, data ):
        if transport_id != 'encrypted_tcp':
            return data
        session = session_list.get_transport_session('test.encrypted_tcp')
        if session is None:
            session = TestSession()
            session.session_key = make_session_key()
            session_list.set_transport_session('test.encrypted_tcp', session)
        packet = encrypt_initial_packet(session.session_key, server_identity.get_public_key(), data)
        return self.encode_packet(transport_id, packet, tEncryptedPacket)

    def decrypt_transport_response_packets( self, session_list, transport_id, packets ):
        if transport_id != 'encrypted_tcp':
            if len(packets) == 0:
                return None  # no response
            self.assertEqual(1, len(packets), repr(packets))
            self.assertEqual(transport_id, packets[0].transport_id)
            return packets[0].data
        session = session_list.get_transport_session('test.encrypted_tcp')
        assert session is not None  # must be created by encrypt_packet
        for packet in packets:
            self.assertEqual(transport_id, packet.transport_id)
            encrypted_packet = self.decode_packet(transport_id, packet.data, tEncryptedPacket)
            if isinstance(encrypted_packet, tSubsequentEncryptedPacket):
                session_key, packet_data = decrypt_packet(server_identity, session.session_key, encrypted_packet)
                return packet_data
        return None  # no response

    def make_tcp_transport_request( self, session_list, transport_id, obj_id, command_id, **kw ):
        request = tRequest(
            iface='test_iface',
            path=[TestModule.name, TestObject.class_name, obj_id],
            command_id=command_id,
            params=test_iface.get_request_params_type(command_id)(**kw),
            request_id='001',
            )
        log.info('Sending request:')
        pprint(tClientPacket, request)
        request_packet = tPacket(
            aux_info=tAuxInfo(requirements=[], modules=[], routes=[], resources=[]),
            payload=self.encode_packet(transport_id, request, tClientPacket))
        request_packet_data = self.encode_packet(transport_id, request_packet, tPacket)
        transport_request = tTransportPacket(
            transport_id=transport_id,
            data=self.encrypt_packet(session_list, transport_id, request_packet_data))
        return transport_request

    def make_tcp_transport_notification( self, session_list, transport_id, obj_id, command_id, **kw ):
        request = tClientNotification(
            iface='test_iface',
            path=[TestModule.name, TestObject.class_name, obj_id],
            command_id=command_id,
            params=test_iface.get_request_params_type(command_id)(**kw),
            )
        log.info('Sending client notification:')
        pprint(tClientPacket, request)
        request_packet = tPacket(
            aux_info=tAuxInfo(requirements=[], modules=[], routes=[], resources=[]),
            payload=self.encode_packet(transport_id, request, tClientPacket))
        request_packet_data = self.encode_packet(transport_id, request_packet, tPacket)
        transport_request = tTransportPacket(
            transport_id=transport_id,
            data=self.encrypt_packet(session_list, transport_id, request_packet_data))
        return transport_request

    def decode_tcp_transport_response( self, session_list, transport_id, response_transport_packets ):
        packet_data = self.decrypt_transport_response_packets(session_list, transport_id, response_transport_packets)
        if packet_data is None:
            return None  # no response
        response_packet = self.decode_packet(transport_id, packet_data, tPacket)
        log.info('Received response:')
        pprint(tPacket, response_packet)
        response = self.decode_packet(transport_id, response_packet.payload, tServerPacket)
        pprint(tServerPacket, response)
        return response

    def execute_tcp_request( self, transport_id, obj_id, command_id, session_list=None, **kw ):
        if session_list is None:
            session_list = self.session_list
        transport_request = self.make_tcp_transport_request(session_list, transport_id, obj_id, command_id, **kw)
        response_transport_packets = self.remoting.process_packet(self.iface_registry, self.server, session_list, transport_request)
        response = self.decode_tcp_transport_response(session_list, transport_id, response_transport_packets)
        return response

    def execute_tcp_notification( self, transport_id, obj_id, command_id, session_list=None, **kw ):
        if session_list is None:
            session_list = self.session_list
        transport_request = self.make_tcp_transport_notification(session_list, transport_id, obj_id, command_id, **kw)
        response_transport_packets = self.remoting.process_packet(self.iface_registry, self.server, self.session_list, transport_request)
        response = self.decode_tcp_transport_response(session_list, transport_id, response_transport_packets)
        self.assertIsNone(response)

    def test_tcp_cdr_echo_request( self ):
        self._test_tcp_echo_request('tcp.cdr')

    def test_tcp_json_echo_request( self ):
        self._test_tcp_echo_request('tcp.json')

    def test_encrypted_tcp_echo_request( self ):
        self._test_tcp_echo_request('encrypted_tcp')

    def _test_tcp_echo_request( self, transport_id ):
        response = self.execute_tcp_request(transport_id, obj_id='1', command_id='echo', test_param='hello')
        self.assertEqual('hello to you too', response.result.test_result)

    def test_tcp_cdr_broadcast_request( self ):
        self._test_broadcast_tcp_request('tcp.cdr')

    def test_tcp_json_broadcast_request( self ):
        self._test_broadcast_tcp_request('tcp.json')

    def test_encrypted_tcp_broadcast_request( self ):
        self._test_broadcast_tcp_request('encrypted_tcp')

    def _test_broadcast_tcp_request( self, transport_id ):
        message = 'hi, all!'
        obj_id = '1'

        response = self.execute_tcp_request(transport_id, obj_id=obj_id, command_id='subscribe')
        response = self.execute_tcp_request(transport_id, obj_id=obj_id, command_id='broadcast', message=message)

        self.assertEqual(1, len(response.updates))
        update = response.updates[0]
        self.assertEqual('test_iface', update.iface)
        self.assertEqual([TestModule.name, TestObject.class_name, obj_id], update.path)
        self.assertEqual(message, update.diff)

    def test_tcp_cdr_unsubscribe_notification_request( self ):
        self._test_unsubscribe_notification_tcp_request('tcp.cdr')

    def test_tcp_json_unsubscribe_notification_request( self ):
        self._test_unsubscribe_notification_tcp_request('tcp.json')

    def test_encrypted_tcp_unsubscribe_notification_request( self ):
        self._test_unsubscribe_notification_tcp_request('encrypted_tcp')

    def _test_unsubscribe_notification_tcp_request( self, transport_id ):
        obj_id = '1'
        response = self.execute_tcp_request(transport_id, obj_id=obj_id, command_id='subscribe')
        response = self.execute_tcp_notification(transport_id, obj_id=obj_id, command_id='unsubscribe')

    def test_tcp_cdr_server_notification( self ):
        self._test_tcp_server_notification('tcp.cdr')

    def test_tcp_json_server_notification( self ):
        self._test_tcp_server_notification('tcp.json')

    def test_encrypted_tcp_server_notification( self ):
        self._test_tcp_server_notification('encrypted_tcp')

    def _test_tcp_server_notification( self, transport_id ):
        message = 'hi, all!'
        obj_id = '1'
        session1 = TransportSessionList()
        session2 = TransportSessionList()

        response = self.execute_tcp_request(transport_id, obj_id=obj_id, command_id='subscribe', session_list=session1)
        response = self.execute_tcp_request(transport_id, obj_id=obj_id, command_id='subscribe', session_list=session2)

        response = self.execute_tcp_request(transport_id, obj_id=obj_id, command_id='broadcast', session_list=session2, message=message)

        notifications = session1.pull_notification_transport_packets()

        self.assertEqual(1, len(notifications))
        notification_packet = notifications[0]
        assert isinstance(notification_packet, tTransportPacket), repr(notification_packet)
        notification = self.decode_tcp_transport_response(session1, transport_id, [notification_packet])
        self.assertEqual(1, len(notification.updates))
        update = notification.updates[0]
        self.assertEqual('test_iface', update.iface)
        self.assertEqual([TestModule.name, TestObject.class_name, obj_id], update.path)
        self.assertEqual(message, update.diff)

    def pick_pop_channelge_from_responses( self, transport_id, response_transport_packets ):
        for packet in response_transport_packets:
            encrypted_packet = self.decode_packet(transport_id, packet.data, tEncryptedPacket)
            if isinstance(encrypted_packet, tPopChallengePacket):
                return encrypted_packet.challenge
        self.fail('No challenge packet in response')

    def encode_pop_transport_request( self, transport_id, challenge, pop_records ):
        pop_packet = tProofOfPossessionPacket(challenge, pop_records)
        pop_packet_data = self.encode_packet(transport_id, pop_packet, tEncryptedPacket)
        return tTransportPacket(transport_id=transport_id, data=pop_packet_data)

    def test_proof_of_possession( self ):
        transport_id = 'encrypted_tcp'
        transport_request = self.make_tcp_transport_request(self.session_list, transport_id, obj_id='1', command_id='echo', test_param='hi')
        response_transport_packets = self.remoting.process_packet(self.iface_registry, self.server, self.session_list, transport_request)
        challenge = self.pick_pop_channelge_from_responses(transport_id, response_transport_packets)

        identity_1 = Identity.generate(fast=True)
        identity_2 = Identity.generate(fast=True)

        pop_record_1 = tPopRecord(
            identity_1.get_public_key().to_der(),
            identity_1.sign(challenge))
        pop_record_2 = tPopRecord(
            identity_2.get_public_key().to_der(),
            identity_2.sign(challenge + b'x'))  # make invlid signature; verification must fail
        transport_request = self.encode_pop_transport_request(transport_id, challenge, [pop_record_1, pop_record_2])

        response_transport_packets = self.remoting.process_packet(self.iface_registry, self.server, self.session_list, transport_request)

        session = self.session_list.get_transport_session(transport_id)
        self.assertIn(identity_1.get_public_key(), session.peer_public_keys)
        self.assertNotIn(identity_2.get_public_key(), session.peer_public_keys)

    # when NotAuthorizedError raised in first request before pop is returned, that request must be reprocessed when pop is processed
    def test_unauthorized_request_reprocess( self ):
        transport_id = 'encrypted_tcp'
        transport_request = self.make_tcp_transport_request(self.session_list, transport_id, obj_id='1', command_id='required_auth')
        response_transport_packets = self.remoting.process_packet(
            self.iface_registry, self.server, self.session_list, transport_request)
        challenge = self.pick_pop_channelge_from_responses(transport_id, response_transport_packets)

        authorized_peer_identity
        
        pop_record = tPopRecord(
            authorized_peer_identity.get_public_key().to_der(),
            authorized_peer_identity.sign(challenge))
        transport_request = self.encode_pop_transport_request(transport_id, challenge, [pop_record])

        response_transport_packets = self.remoting.process_packet(
            self.iface_registry, self.server, self.session_list, transport_request)

        response = self.decode_tcp_transport_response(self.session_list, transport_id, response_transport_packets)
        self.assertIsNotNone(response)  # now, after pop is received, first request must be processed
        self.assertEqual('ok', response.result.test_result)


if __name__ == '__main__':
    unittest.main()
