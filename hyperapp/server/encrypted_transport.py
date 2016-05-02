import os
from Queue import Queue
from ..common.util import flatten
from ..common.htypes import tClientPacket, tServerPacket
from ..common.packet import tAuxInfo, tPacket, Packet
from ..common.transport_packet import tTransportPacket
from ..common.encrypted_packet import (
    ENCODING,
    POP_CHALLENGE_SIZE,
    tEncryptedPacket,
    tInitialEncryptedPacket,
    tSubsequentEncryptedPacket,
    tPopChallengePacket,
    tProofOfPossessionPacket,
    encrypt_subsequent_packet,
    decrypt_packet,
    )
from ..common.packet_coders import packet_coders
from ..common.visual_rep import pprint
from ..common.identity import PublicKey
from .request import NotAuthorizedError, PeerChannel, Peer, RequestBase, ServerNotification
from .transport import Transport, transport_registry
from .transport_session import TransportSession
from .server import Server


class EncryptedTcpChannel(PeerChannel):

    def __init__( self, transport ):
        self.transport = transport
        self.updates = Queue()  # tUpdate list

    def _pop_all( self ):
        updates = []
        while not self.updates.empty():
            updates.append(self.updates.get())
        return list(reversed(updates))

    def send_update( self, update ):
        print '    update to be sent to %r channel %s' % (self.transport.get_transport_id(), self.get_id())
        self.updates.put(update)

    def pop_updates( self ):
        return self._pop_all()


class EncryptedTcpSession(TransportSession):

    def __init__( self, transport ):
        assert isinstance(transport, EncryptedTcpTransport), repr(transport)
        TransportSession.__init__(self)
        self.transport = transport
        self.channel = EncryptedTcpChannel(transport)
        self.session_key = None
        self.pop_challenge = None  # str
        self.pop_challenge_sent = False
        self.pop_received = False
        self.peer_public_keys = []  # verified using pop
        self.requests_waiting_for_pop = []  # Request list

    def pull_notification_transport_packets( self ):
        updates = self.channel._pop_all()
        if not updates:
            return []
        notification = ServerNotification()
        for update in updates:
            notification.add_update(update)
        notification_data = notification.to_data()
        aux_info = Server.prepare_aux_info(notification_data)
        print '-- sending notification to %r channel %s' % (self.transport.get_transport_id(), self.get_id())
        pprint(tAuxInfo, aux_info)
        pprint(tServerPacket, notification_data)
        encrypted_packet = self.transport.encode_response_or_notification(self, aux_info, notification_data)
        packet_data = packet_coders.encode(ENCODING, encrypted_packet, tEncryptedPacket)
        return [tTransportPacket.instantiate(self.transport.get_transport_id(), packet_data)]


class EncryptedTcpTransport(Transport):

    def get_transport_id( self ):
        return 'encrypted_tcp'

    def register( self, registry ):
        registry.register(self.get_transport_id(), self)

    def process_packet( self, iface_registry, server, session_list, data ):
        session = session_list.get_transport_session(self.get_transport_id())
        if session is None:
           session = EncryptedTcpSession(self)
           session_list.set_transport_session(self.get_transport_id(), session)
        encrypted_packet = packet_coders.decode(ENCODING, data, tEncryptedPacket)
        pprint(tEncryptedPacket, encrypted_packet)
        if tEncryptedPacket.isinstance(encrypted_packet, tSubsequentEncryptedPacket):
            responses = self.process_encrypted_payload_packet(iface_registry, server, session, encrypted_packet)
        if tEncryptedPacket.isinstance(encrypted_packet, tProofOfPossessionPacket):
            responses = self.process_pop_packet(session, encrypted_packet)
        if session.pop_received:
            responses += flatten([self.process_postponed_request(server, session, request) for request in session.requests_waiting_for_pop])
            session.requests_waiting_for_pop = []
        if not session.pop_challenge_sent:
            responses.append(self.make_pop_challenge_packet(session))
            session.pop_challenge_sent = True
        for response in responses:
            pprint(tEncryptedPacket, response)
        return [packet_coders.encode(ENCODING, encrypted_packet, tEncryptedPacket)
                for encrypted_packet in responses]

    def process_encrypted_payload_packet( self, iface_registry, server, session, encrypted_packet ):
        packet_data = self.decrypt_packet(server, session, encrypted_packet)
        packet = packet_coders.decode(ENCODING, packet_data, tPacket)
        request_rec = packet_coders.decode(ENCODING, packet.payload, tClientPacket)
        pprint(tClientPacket, request_rec)
        request = RequestBase.from_data(server, Peer(session.channel, session.peer_public_keys), iface_registry, request_rec)

        try:
            result = server.process_request(request)
            return self.encode_request_result(session, result)
        except NotAuthorizedError:
            if session.pop_received:
                raise
            session.requests_waiting_for_pop.append(request)
            print 'Request is postponed until POP is received', request
            return []

    def process_postponed_request( self, server, session, request ):
        print 'Reprocessing postponed request', request
        request.peer.public_keys = session.peer_public_keys  # this may change since request was first created
        result = server.process_request(request)
        return self.encode_request_result(session, result)

    def encode_request_result( self, session, result ):
        if result is None:
            return []
        aux_info, response_or_notification = result
        pprint(tAuxInfo, aux_info)
        pprint(tServerPacket, response_or_notification)
        return [self.encode_response_or_notification(session, aux_info, response_or_notification)]

    def process_pop_packet( self, session, encrypted_packet ):
        print 'POP received'
        if encrypted_packet.challenge != session.pop_challenge:
            print 'Error processing POP: challenge does not match'  # todo: return error
            return
        for rec in encrypted_packet.pop_records:
            public_key = PublicKey.from_der(rec.public_key_der)
            if public_key.verify(session.pop_challenge, rec.signature):
                session.peer_public_keys.append(public_key)
                print 'Peer public key %s is verified' % public_key.get_short_id_hex()
            else:
                print 'Error processing POP record for %s: signature does not match' % public_key.get_short_id_hex()  # todo: return error
        session.pop_received = True
        return []

    def encode_response_or_notification( self, session, aux_info, response_or_notification ):
        assert session.session_key  # must be set when initial packet is received
        payload = packet_coders.encode(ENCODING, response_or_notification, tServerPacket)
        packet = Packet(aux_info, payload)
        packet_data = packet_coders.encode(ENCODING, packet, tPacket)
        return encrypt_subsequent_packet(session.session_key, packet_data)

    def decrypt_packet( self, server, session, encrypted_packet ):
        if not tEncryptedPacket.isinstance(encrypted_packet, tInitialEncryptedPacket):
            assert session.session_key, tEncryptedPacket.resolve_obj(encrypted_packet).id  # subsequent packet must not be first one
        session_key, plain_text = decrypt_packet(server.get_identity(), session.session_key, encrypted_packet)
        session.session_key = session_key
        return plain_text

    def make_pop_challenge_packet( self, session ):
        print 'sending pop challenge:'
        challenge = os.urandom(POP_CHALLENGE_SIZE/8)
        session.pop_challenge = challenge
        return tPopChallengePacket.instantiate(
            challenge=challenge)


EncryptedTcpTransport().register(transport_registry)
