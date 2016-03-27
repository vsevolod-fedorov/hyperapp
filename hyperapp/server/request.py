from ..common.htypes import tUpdate, tClientPacket, tClientNotification, tRequest, tServerNotification, tResponse


class PeerChannel(object):

    def get_id( self ):
        return hex(id(self))[-6:]

    def send_update( self, update ):
        raise NotImplementedError(self.__class__)

    def pop_updates( self ):
        raise NotImplementedError(self.__class__)


class RequestBase(object):

    @classmethod
    def from_data( cls, me, peer_channel, iface_registry, rec ):
        assert isinstance(peer_channel, PeerChannel), repr(peer_channel)
        tClientPacket.validate('<ClientPacket>', rec)
        iface = iface_registry.resolve(rec.iface)
        if tClientPacket.isinstance(rec, tRequest):
            return Request(me, peer_channel, iface, rec.path, rec.command_id, rec.request_id, rec.params)
        else:
            assert tClientPacket.isinstance(rec, tClientNotification), repr(rec)
            return ClientNotification(me, peer_channel, iface, rec.path, rec.command_id, rec.params)

    def __init__( self, me, peer_channel, iface, path, command_id, params ):
        self.me = me      # Server instance
        self.peer_channel = peer_channel
        self.iface = iface
        self.path = path
        self.command_id = command_id
        self.params = params


class ClientNotification(RequestBase):
    pass


class Request(RequestBase):

    def __init__( self, me, peer_channel, iface, path, command_id, request_id, params ):
        RequestBase.__init__(self, me, peer_channel, iface, path, command_id, params)
        self.request_id = request_id

    def make_response( self, result=None ):
        result_type = self.iface.get_command_result_type(self.command_id)
        result_type.validate('%s.Request.%s.result' % (self.iface.iface_id, self.command_id), result)
        return Response(self.peer_channel, self.iface, self.command_id, self.request_id, result)

    def make_response_object( self, obj ):
        return self.make_response(obj)

    def make_response_handle( self, obj ):
        return self.make_response(obj.get_handle())

    def make_response_result( self, **kw ):
        return self.make_response(self.iface.make_result(self.command_id, **kw))

    def make_response_update( self, iface, path, diff ):
        response = self.make_response()
        response.add_update(iface.Update(path, diff))
        return response



class ResponseBase(object):

    def __init__( self ):
        self.updates = []

    def add_update( self, update ):
        tUpdate.validate('<Update>', update)
        self.updates.append(update)


class ServerNotification(ResponseBase):

    def to_data( self ):
        return tServerNotification.instantiate(self.updates)


class Response(ResponseBase):

    def __init__( self, peer, iface, command_id, request_id, result ):
        ResponseBase.__init__(self)
        self.peer = peer
        self.iface = iface
        self.command_id = command_id
        self.request_id = request_id
        self.result = result

    def to_data( self ):
        return tResponse.instantiate(self.updates, self.iface.iface_id, self.command_id, self.request_id, self.result)
