from common.util import path2str
from common.interface import (
    tString,
    Field,
    ObjHandle,
    iface_registry,
    )
import common.interface.interface as interface_module
import common.interface.list as list_module
from util import WeakValueMultiDict
from common.interface import Interface


MIN_ROWS_RETURNED = 10


class Subscription(object):

    def __init__( self ):
        self.path2client = WeakValueMultiDict()  # path -> client

    def add( self, path, client ):
        self.path2client.add(path2str(path), client)

    def remove( self, path, client ):
        self.path2client.remove(path2str(path), client)

    def distribute_update( self, iface, path, diff ):
        update = iface.Update(path, diff)
        for client in self.path2client.get(path2str(path)):
            client.send_update(update)


subscription = Subscription()


class Object(interface_module.Object):

    def __init__( self ):
        pass

    def get_path( self ):
        raise NotImplementedError(self.__class__)

    def get_commands( self ):
        return []

    def get( self ):
        return self.iface.Object(
            iface=self.iface,
            proxy_id=self.proxy_id,
            path=self.get_path(),
            contents=self.get_contents(),
            )

    def get_contents( self, **kw ):
        return self.iface.Contents(
            commands=self.get_commands(),
            **kw)

    def get_handle( self ):
        raise NotImplementedError(self.__class__)

    def process_request( self, request ):
        command_id = request.command_id
        if command_id == 'get':
            return self.process_request_get(request)
        if command_id == 'subscribe':
            return self.process_request_subscribe(request)
        elif command_id == 'subscribe':
            self.subscribe(request)
        elif command_id == 'unsubscribe':
            self.unsubscribe(request)
        else:
            assert False, repr(command_id)  # Unknown command

    def process_request_get( self, request ):
        self.subscribe(request)
        return request.make_response(self.get_handle())

    def process_request_subscribe( self, request ):
        self.subscribe(request)
        return request.make_response(self.get_contents())

    def subscribe( self, request ):
        subscription.add(self.get_path(), request.peer)

    def unsubscribe( self, request ):
        subscription.remove(self.get_path(), request.peer)


class ListObject(Object, list_module.ListObject):

    def __init__( self ):
        Object.__init__(self)
        self.key_column_idx = self._pick_key_column_idx(self.get_columns())

    def _pick_key_column_idx( self, columns ):
        for idx, column in enumerate(self.get_columns()):
            if column.id == 'key':
                return idx
        assert False, 'Missing "key" column id'

    def get_contents( self, selected_key=None, **kw ):
        elements, has_more = self.get_elements()
        return Object.get_contents(self,
            columns=self.get_columns(),
            elements=elements,
            has_more=has_more,
            selected_key=selected_key,
            **kw)

    def get_handle( self ):
        return self.ListHandle(self)

    def process_request( self, request ):
        if request.command_id == 'get_elements':
            key = request.params.key
            count = request.params.count
            elements, has_more = self.get_elements(count, key)
            return request.make_response_result(fetched_elements=self.FetchedElements(
                elements=elements,
                has_more=has_more))
            return response
        elif request.command_id == 'run_element_command':
            command_id = request.command_id
            element_key = request.params.element_key
            return self.run_element_command(request, command_id, element_key)
        else:
            return Object.process_request(self, request)

    def get_columns( self ):
        return self.columns

    def get_elements( self, count=None, from_key=None ):
        elements = self.get_all_elements()
        from_idx = 0
        if from_key is not None:
            for idx, elt in enumerate(elements):
                if elt.row[self.key_column_idx] == from_key:
                    from_idx = idx + 1
                    break
            else:
                print 'Warning: unknown "from_key" is requested: %r' % from_key
        to_idx = from_idx + max(count or 0, MIN_ROWS_RETURNED)
        has_more = to_idx <= len(elements)
        return (elements[from_idx:to_idx], has_more)

    def get_all_elements( self ):
        raise NotImplementedError(self.__class__)

    def run_element_command( self, request, command_id, element_key ):
        assert False, repr(command_id)  # Unexpected command_id
