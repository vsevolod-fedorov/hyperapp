# Rationale for using __new__ to resolve  proxies from registry:
# I need to keep single proxy object per path for subscription/notification to work.
# This must work even when unpickling objects. Another solution for pickling/unpickling could be
# persistent_id/persistend_load mechanism, but in that case class and state information
# stored in pickle would be lost. I would need to construct proxy objects by myself then if unpickled
# instance is first with this 'path'.

import weakref
import uuid
from common.interface import Interface, Field, tString, tPath, resolve_iface
import common.interface as interface_module
from common.request import ClientNotification, Request
from .object import Object
from .command import Command
from .list_object import ListDiff, Element, Slice, ListObject
from . import proxy_registry
from . import view


class RespHandler(proxy_registry.RespHandler):

    def __init__( self, object, command_id, initiator_view ):
        assert isinstance(object, Object), repr(object)
        proxy_registry.RespHandler.__init__(self, object.iface, command_id)
        assert initiator_view is None or isinstance(initiator_view, view.View), repr(initiator_view)
        self.object = weakref.ref(object)
        self.initiator_view = weakref.ref(initiator_view) if initiator_view else None  # may be initiated not by a view

    def process_response( self, server, response ):
        object = self.object()
        initiator_view = self.initiator_view() if self.initiator_view else None
        if object:
            object.process_response(server, response, self, self.command_id, initiator_view)


class ProxyObject(Object, interface_module.Object):

    @classmethod
    def decode( cls, server, path, iface, contents ):
        object = cls(server, path, iface)
        object.set_contents(contents)
        return object

    # this schema allows resolving/deduplicating objects while unpickling
    def __new__( cls, server, path, *args, **kw ):
        obj = proxy_registry.resolve_proxy(path)
        if obj:
            return obj
        else:
            return object.__new__(cls, server, path, *args, **kw)

    def __init__( self, server, path, iface ):
        if hasattr(self, 'init_flag'): return   # after __new__ returns resolved object __init__ is called anyway
        Object.__init__(self)
        interface_module.Object.__init__(self)
        self.init_flag = None
        self.server = server
        self.path = path
        self.iface = iface
        self.commands = []
        self.resp_handlers = set()  # explicit refs to ObjectRespHandlers to keep them alive until object is alive
        proxy_registry.register_proxy(self.path, self)

    def __getnewargs__( self ):
        return (self.server, self.path)

    def __getstate__( self ):
        state = Object.__getstate__(self)
        del state['resp_handlers']
        del state['iface']
        state['iface_id'] = self.iface.iface_id
        return state

    def __setstate__( self, state ):
        if hasattr(self, 'init_flag'): return  # after __new__ returns resolved object __setstate__ is called anyway too
        Object.__setstate__(self, state)
        self.iface = resolve_iface(state['iface_id'])
        self.resp_handlers = set()
        proxy_registry.register_proxy(self.path, self)

    @staticmethod
    def get_proxy_id():
        return 'object'

    def subscribe( self, observer ):
        this_is_first_observer = Object.subscribe(self, observer)
        if this_is_first_observer:
            self.execute_request('subscribe')

    def set_contents( self, contents ):
        self.commands = map(Command.decode, contents.commands)

    def get_title( self ):
        return '/' + '/'.join(self.path)

    def get_commands( self ):
        return self.commands

    def run_command( self, command_id, initiator_view=None, **kw ):
        self.execute_request(command_id, initiator_view, **kw)

    def observers_gone( self ):
        self.send_notification('unsubscribe')

    # prepare request which does not require/expect response
    def prepare_notification( self, command_id, *args, **kw ):
        params = self.iface.make_params(command_id, *args, **kw)
        return ClientNotification(self.server, self.iface, self.path, command_id, params=params)

    def prepare_request( self, command_id, *args, **kw ):
        request_id = str(uuid.uuid4())
        params = self.iface.make_params(command_id, *args, **kw)
        return Request(self.server, self.iface, self.path, command_id, request_id, params=params)

    def send_notification( self, command_id, *args, **kw ):
        request = self.prepare_notification(command_id, *args, **kw)
        self.server.send_notification(request)

    def execute_request( self, command_id, initiator_view=None, *args, **kw ):
        request = self.prepare_request(command_id, *args, **kw)
        resp_handler = RespHandler(self, command_id, initiator_view)
        self.resp_handlers.add(resp_handler)
        self.server.execute_request(request, resp_handler)

    def process_response( self, server, response, resp_handler, command_id, initiator_view ):
        result = response.result
        self.process_response_result(command_id, result)
        self.resp_handlers.remove(resp_handler)
        # initiator_view may already be gone (closed, navigated away) or be missing at all - so is None
        if self.iface.is_open_command(command_id) and initiator_view:
            initiator_view.process_handle_open(server, result)

    def process_response_result( self, command_id, result ):
        if command_id == 'subscribe':
            self.process_subscribe_response(result)

    def process_subscribe_response( self, result ):
        self.set_contents(result)
        self._notify_object_changed()

    def process_update( self, diff ):
        raise NotImplementedError(self.__class__)

    def __del__( self ):
        print '~ProxyObject', self, self.path


class ProxyListObject(ProxyObject, ListObject):

    def __init__( self, server, path, iface ):
        ProxyObject.__init__(self, server, path, iface)
        ListObject.__init__(self)
        self.fetch_pending = False  # has pending element fetch request

    @staticmethod
    def get_proxy_id():
        return 'list'

    def set_contents( self, contents ):
        ProxyObject.set_contents(self, contents)
        self._initial_slice = self._decode_slice(contents)

    # We can use initial slice only once, immediately after receiving object contents.
    # After that contents may change
    def get_initial_slice( self ):
        slice = self._initial_slice
        self._initial_slice = None
        return slice

    def _decode_slice( self, rec ):
        key_column_id = self.get_key_column_id()
        elements = [Element.decode(key_column_id, elt_rec) for elt_rec in rec.elements]
        return Slice(rec.sort_column_id, elements, rec.bof, rec.eof)

    def subscribe_and_fetch_elements( self, observer, sort_column_id, key, desc_count, asc_count ):
        this_is_first_observer = self.subscribe_local(observer)
        if not this_is_first_observer: return
        self.execute_request('subscribe_and_fetch_elements', None, sort_column_id, key, desc_count, asc_count)
        self.fetch_pending = True

    def process_update( self, diff ):
        print 'process_update', self, diff, diff.start_key, diff.end_key, diff.elements
        key_column_id = self.get_key_column_id()
        self._notify_diff_applied(ListDiff.decode(key_column_id, diff))

    def get_columns( self ):
        return self.iface.columns

    def get_key_column_id( self ):
        return self.iface.key_column

    def fetch_elements( self, sort_column_id, key, desc_count, asc_count ):
        if self.fetch_pending: return
        self.execute_request('fetch_elements', None, sort_column_id, key, desc_count, asc_count)
        self.fetch_pending = True

    def process_response_result( self, command_id, result ):
        if command_id in ['fetch_elements', 'subscribe_and_fetch_elements']:
            self.process_fetch_elements_result(result)
        ProxyObject.process_response_result(self, command_id, result)

    def process_fetch_elements_result( self, result ):
        self.fetch_pending = False
        slice = self._decode_slice(result)
        self._notify_fetch_result(slice)

    def __del__( self ):
        print '~ProxyListObject', self, self.path


proxy_registry.register_iface(ProxyObject)
proxy_registry.register_iface(ProxyListObject)
