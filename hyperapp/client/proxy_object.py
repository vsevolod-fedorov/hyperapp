import weakref
import uuid
from ..common.endpoint import Endpoint, Url
from ..common.interface import (
    Interface,
    Field,
    tString,
    TRecord,
    tObject,
    tThisProxyObject,
    tProxyObject,
    tThisProxyObjectWithContents,
    tHandle,
    tViewHandle,
    tRedirectHandle,
    tPath,
    tEndpoint,
    resolve_iface,
    iface_registry,
    )
from .object import Object
from .command import Command
from .proxy_registry import proxy_class_registry, proxy_registry
from .request import ClientNotification, Request
from .server import Server
from .get_request import run_get_request
from . import view
from ..common.redirect_handle_resolver import RedirectHandleCollector



class ObjRequest(Request):

    def __init__( self, iface, path, command_id, request_id, params, object, initiator_view ):
        assert isinstance(object, Object), repr(object)
        assert initiator_view is None or isinstance(initiator_view, view.View), repr(initiator_view)
        Request.__init__(self, iface, path, command_id, request_id, params)
        self.object = weakref.ref(object)
        self.initiator_view = weakref.ref(initiator_view) if initiator_view else None  # may be initiated not by a view

    def process_response( self, server, response ):
        object = self.object()
        initiator_view = self.initiator_view() if self.initiator_view else None
        if object:
            object.process_response(self, initiator_view, server, response)


class ProxyObject(Object):

    @staticmethod
    def resolve_persistent_id( persistent_id ):
        parts = decode_url(persistent_id)
        objimpl_id, iface_id = parts[:2]
        url = parts[2:]
        server, path = Server.resolve_url(url)
        iface = iface_registry.resolve(iface_id)
        proxy_cls = proxy_class_registry.resolve(objimpl_id)
        return proxy_cls.produce_obj(server, path, iface)

    @classmethod
    def produce_obj_by_objinfo( cls, objinfo, server=None ):
        assert tObject.isinstance(objinfo, tThisProxyObject) or tObject.isinstance(objinfo, tProxyObject), repr(objinfo)
        if server is None:
            assert tObject.isinstance(objinfo, tProxyObject), repr(objinfo)  # we need endpoint somehow
            server = Server.produce(Endpoint.from_data(objinfo.endpoint))
        iface = iface_registry.resolve(objinfo.iface)
        object = cls.produce_obj(server, objinfo.path, iface)
        if tObject.isinstance(objinfo, tThisProxyObjectWithContents):  # is it a response?
            object.set_contents(objinfo.contents)
        return object

    # we avoid making proxy objects with same server+path
    @classmethod
    def produce_obj( cls, server, path, iface ):
        object = proxy_registry.resolve(server, path)
        if object is not None:
            print '> proxy object is resolved from registry:', object
            return object
        object = cls(server, path, iface)
        proxy_registry.register(server, path, object)
        print '< proxy object is registered in registry:', object
        return object

    def __init__( self, server, path, iface ):
        Object.__init__(self)
        self.server = server
        self.path = path
        self.iface = iface
        self.commands = []

    def to_data( self ):
        return tProxyObject.instantiate(
            self.get_objimpl_id(),
            self.iface.iface_id,
            self.path,
            self.server.get_endpoint().to_data(),
            )

    def get_url( self ):
        return self.server.make_url(self.path)

    def get_module_ids( self ):
        return self.iface.get_module_ids()

    ## def get_persistent_id( self ):
    ##     return encode_url([self.get_objimpl_id(),
    ##                        self.iface.iface_id] + self.server.make_url(self.path))

    @classmethod
    def get_objimpl_id( cls ):
        return 'object'

    def server_subscribe( self ):
        self.execute_request('subscribe')

    def set_contents( self, contents ):
        self.commands = map(Command.decode, contents.commands)

    def get_title( self ):
        return '%s:%s' % (self.server.endpoint.public_key.get_short_id_hex(), '|'.join(self.path))

    def get_commands( self ):
        return self.commands

    def run_command( self, command_id, initiator_view=None, **kw ):
        self.execute_request(command_id, initiator_view, **kw)

    def observers_gone( self ):
        print '-- observers_gone', self
        self.send_notification('unsubscribe')

    # prepare request which does not require/expect response
    def prepare_notification( self, command_id, *args, **kw ):
        params = self.iface.make_params(command_id, *args, **kw)
        return ClientNotification(self.iface, self.path, command_id, params=params)

    def prepare_request( self, command_id, initiator_view, *args, **kw ):
        request_id = str(uuid.uuid4())
        params = self.iface.make_params(command_id, *args, **kw)
        return ObjRequest(self.iface, self.path, command_id, request_id, params, self, initiator_view)

    def send_notification( self, command_id, *args, **kw ):
        request = self.prepare_notification(command_id, *args, **kw)
        self.server.send_notification(request)

    def execute_request( self, command_id, initiator_view=None, *args, **kw ):
        request = self.prepare_request(command_id, initiator_view, *args, **kw)
        self.server.execute_request(request)

    def process_response( self, request, initiator_view, server, response ):

        result_type = request.iface.get_command_result_type(request.command_id)
        redirect_handles = RedirectHandleCollector.collect(result_type, response.result)
        if redirect_handles:
            self.run_resolve_redirect_request(request.command_id, response.result, redirect_handles)
            return

        self.process_response_result(request.command_id, response.result)
        # initiator_view may already be gone (closed, navigated away) or be missing at all - so is None
        if self.iface.is_open_command(request.command_id) and initiator_view:
            handle = response.result
            if tHandle.isinstance(handle, tViewHandle):
                initiator_view.process_handle_open(handle, server)
            elif tHandle.isinstance(handle, tRedirectHandle):
                run_get_request(initiator_view, Url.from_data(handle.redirect_to))
            else:
                assert False, repr(tHandle.resolve_obj(handle).id)  # Unknown handle class

    def process_response_result( self, command_id, result ):
        if command_id == 'subscribe':
            self.process_subscribe_response(result)

    def process_subscribe_response( self, result ):
        self.set_contents(result)
        self._notify_object_changed()

    def run_resolve_redirect_request( self, command_id, result, redirect_handles ):
        assert len(redirect_handles) == 1  # multiple redirects in one response is not supported (yet?)
        

    def process_update( self, diff ):
        raise NotImplementedError(self.__class__)

    def __del__( self ):
        print '~ProxyObject', self, self.path


proxy_class_registry.register(ProxyObject)
