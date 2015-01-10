from object import Object


class Iface(object):

    id = None

    def get( self, object ):
        if object is None: return None
        return dict(
            object.get_json(),
            iface_id=self.id,
            )

    def process_request( self, object, method, request ):
        if method == 'get':
            return object.iface.get(object)
        if method == 'run_command':
            command_id = request['command_id']
            response = object.run_command(command_id, request)
            if isinstance(response, Object):
                new_object = response
                response = new_object.iface.get(new_object)
            return response
        else:
            assert False, repr(method)  # Unknown method


class ObjectIface(Iface):

    id = 'object'


class TextObjectIface(Iface):

    id = 'text'


class ListIface(Iface):

    id = 'list'

    def get( self, object ):
        if object is None: return None
        return dict(
            Iface.get(self, object),
            columns=[column.as_json() for column in object.columns],
            elements=self.get_elements(object))

    def get_elements( self, object, count=None, key=None ):
        return [elt.as_json() for elt in object.get_elements(count, key)]

    def process_request( self, object, method, request ):
        if method == 'get_elements':
            key = request['key']
            count = request['count']
            return dict(elements=self.get_elements(object, count, key))
        elif method == 'run_element_command':
            command_id = request['command_id']
            element_key = request['element_key']
            new_object = object.run_element_command(command_id, element_key)
            return new_object.iface.get(new_object)
        else:
            return Iface.process_request(self, object, method, request)
