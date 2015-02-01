

MIN_ROWS_RETURNED = 10


class Column(object):

    def __init__( self, id, title=None, type='str' ):
        self.id = id
        self.title = title
        self.type = type

    def as_json( self ):
        return dict(
            id=self.id,
            title=self.title,
            type=self.type
            )


class Element(object):

    def __init__( self, key, row, commands=None ):
        self.key = key
        self.row = row  # value list
        self.commands = commands or []

    def as_json( self ):
        return dict(
            row=self.row,
            commands=[cmd.as_json() for cmd in self.commands],
            )


class Command(object):

    def __init__( self, id, text, desc, shortcut=None ):
        self.id = id
        self.text = text
        self.desc = desc
        self.shortcut = shortcut

    def as_json( self ):
        return dict(
            id=self.id,
            text=self.text,
            desc=self.desc,
            shortcut=self.shortcut,
            )


class Response(object):

    def __init__( self, action, **kw ):
        self.action = action
        self.data = kw

    def as_json( self ):
        return dict(
            action=self.action,
            **self.data)


class ObjectBase(object):

    def response( self, open=None ):
        if open is not None:
            assert isinstance(open, Object), repr(open)
            open_obj = open.get()
        else:
            open_obj = None
        return Response('open', obj=open_obj)

    def adapt_response( self, response ):
        if isinstance(response, Response):
            return response
        if isinstance(response, Object):
            return Response('open', obj=response.get())
        if response is None:
            return None
        assert False, repr(response)  # self.response must be used for returning responses or an object instance must be returned

    def process_request( self, request ):
        method = request['method']
        if method == 'run_command':
            command_id = request['command_id']
            response = self.run_command(command_id, request)
            return self.adapt_response(response)
        else:
            assert False, repr(method)  # Unknown method

    def run_command( self, command_id, request ):
        assert False, repr(command_id)  # Unknown command


class Object(ObjectBase):

    def __init__( self, path ):
        self.path = path

    def get_path( self ):
        return self.path

    def get_commands( self ):
        return []

    def get( self, **kw ):
        return dict(
            iface_id=self.iface.id,
            view_id=self.view_id,
            path=self.get_path(),
            commands=[cmd.as_json() for cmd in self.get_commands()],
            **kw)

    def response( self, open=None ):
        if open is not None:
            assert isinstance(open, Object), repr(open)
            open_obj = open.get()
        else:
            open_obj = None
        return Response('open', obj=open_obj)

    def process_request( self, request ):
        method = request['method']
        if method == 'get':
            return Response('open', obj=self.get())
        else:
            return ObjectBase.process_request(self, request)


class ListObject(Object):

    def __init__( self, path ):
        Object.__init__(self, path)
        self.key_column_idx = self._pick_key_column_idx(self.get_columns())

    def _pick_key_column_idx( self, columns ):
        for idx, column in enumerate(self.get_columns()):
            if column.id == 'key':
                return idx
        assert False, 'Missing "key" column id'

    def get( self, **kw ):
        elements, has_more = self.get_elements_json()
        return Object.get(self,
            columns=[column.as_json() for column in self.get_columns()],
            elements=elements,
            has_more=has_more,
            **kw)

    def get_elements_json( self, count=None, key=None ):
        elements, has_more = self.get_elements(count, key)
        return ([elt.as_json() for elt in elements], has_more)

    def process_request( self, request ):
        method = request['method']
        if method == 'get_elements':
            key = request['key']
            count = request['count']
            elements, has_more = self.get_elements_json(count, key)
            return Response('fetched_elements',
                            elements=elements,
                            has_more=has_more)
        elif method == 'run_element_command':
            command_id = request['command_id']
            element_key = request['element_key']
            response = self.run_element_command(command_id, element_key)
            return self.adapt_response(response)
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

    def run_element_command( self, command_id, element_key ):
        assert False, repr(command_id)  # Unexpected command_id
