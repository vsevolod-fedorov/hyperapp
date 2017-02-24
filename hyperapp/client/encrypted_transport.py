import asyncio
from ..common.encrypted_packet import (
    tEncryptedPacket,
    tSubsequentEncryptedPacket,
    tPopChallengePacket,
    tPopRecord,
    tProofOfPossessionPacket,
    make_session_key,
    encrypt_initial_packet,
    decrypt_subsequent_packet,
    )
from ..common.transport_packet import tTransportPacket, encode_transport_packet, decode_transport_packet
from ..common.visual_rep import pprint
from ..common.packet_coders import packet_coders
from .request import ResponseBase
from .remoting import Transport
from .tcp_protocol import TcpProtocol


TRANSPORT_ID = 'encrypted_tcp'
ENCODING = 'cdr'


def register_transports( registry, services ):
    registry.register(TRANSPORT_ID, EncryptedTransport(services))


class Session(object):

    def __init__( self, session_key ):
        assert isinstance(session_key, bytes), repr(session_key)
        self.session_key = session_key


class EncryptedTransport(Transport):

    @asyncio.coroutine
    def send_request_rec( self, remoting, public_key, route, request_or_notification ):
        assert len(route) >= 2, repr(route)  # host and port are expected
        host, port_str = route[:2]
        port = int(port_str)
        protocol = yield from TcpProtocol.produce(remoting, public_key, host, port)
        session = self._produce_session(protocol.session_list)
        transport_packet = self._make_payload_packet(session, public_key, request_or_notification)
        protocol.send_packet(transport_packet)
        return True

    def _produce_session( self, session_list ):
        session = session_list.get_transport_session(TRANSPORT_ID)
        if session is None:
            session_key = make_session_key()
            session = Session(session_key)
            session_list.set_transport_session(TRANSPORT_ID, session)
        return session
    
    def _make_payload_packet( self, session, server_public_key, request_or_notification ):
        packet = self.make_request_packet(ENCODING, request_or_notification)
        packet_data = packet_coders.encode(ENCODING, packet, tPacket)
        encrypted_packet = encrypt_initial_packet(session.session_key, server_public_key, packet_data)
        return self._make_transport_packet(encrypted_packet)

    def _make_transport_packet( self, encrypted_packet ):
        encrypted_packet_data = packet_coders.encode(ENCODING, encrypted_packet, tEncryptedPacket)
        return tTransportPacket(TRANSPORT_ID, encrypted_packet_data)

    @asyncio.coroutine
    def process_packet( self, protocol, session_list, server_public_key, data ):
        session = session_list.get_transport_session(TRANSPORT_ID)
        assert session is not None  # must be created when sending request
        encrypted_packet = packet_coders.decode(ENCODING, data, tEncryptedPacket)
        if isinstance(encrypted_packet, tSubsequentEncryptedPacket):
            return (yield from self._process_subsequent_encrypted_packet(server_public_key, session, encrypted_packet))
        if isinstance(encrypted_packet, tPopChallengePacket):
            yield from self._process_pop_challenge_packet(protocol, server_public_key, session, encrypted_packet)
            return None  # not a response; packet processed by transport

    @asyncio.coroutine
    def _process_subsequent_encrypted_packet( self, server_public_key, session, encrypted_packet ):
        packet_data = decrypt_subsequent_packet(session.session_key, encrypted_packet)
        packet = packet_coders.decode(ENCODING, packet_data, tPacket)
        pprint(tPacket, packet)
        yield from self.process_aux_info(packet.aux_info)
        response_or_notification_rec = packet_coders.decode(ENCODING, packet.payload, self._request_types.tServerPacket)
        pprint(self._request_types.tServerPacket, response_or_notification_rec)
        return ResponseBase.from_data(self._request_types, self._iface_registry, server_public_key, response_or_notification_rec)

    @asyncio.coroutine
    def _process_pop_challenge_packet( self, protocol, server_public_key, session, encrypted_packet ):
        challenge = encrypted_packet.challenge
        pop_records = []
        for item in self._identity_controller.get_items():
            pop_records.append(tPopRecord(
                item.identity.get_public_key().to_der(),
                item.identity.sign(challenge)))
        pop_packet = tProofOfPossessionPacket(challenge, pop_records)
        transport_packet = self._make_transport_packet(pop_packet)
        protocol.send_packet(transport_packet)
