from util import path2str, WeakValueMultiDict


MIN_ROWS_RETURNED = 10


class Subscription(object):

    def __init__( self ):
        self.path2client = WeakValueMultiDict()  # path -> client

    def add( self, path, client ):
        self.path2client.add(path2str(path), client)

    def remove( self, path, client ):
        self.path2client.remove(path2str(path), client)

    def distribute_update( self, path, diff ):
        assert isinstance(diff, ListDiff), repr(diff)
        for client in self.path2client.get(path2str(path)):
            client.send_update(path, diff)


subscription = Subscription()


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
            key=self.key,
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


class ListDiff(object):

    @classmethod
    def add_one( cls, key, element ):
        return cls(key, key, [element])

    @classmethod
    def delete( cls, key ):
        return cls(key, key + 1, [])

    def __init__( self, start_key, end_key, elements ):
        self.start_key = start_key  # replace elements from this one
        self.end_key = end_key      # up to (but not including) this one
        self.elements = elements    # with these elemenents

    def as_json( self ):
        return dict(
            start_key=self.start_key,
            end_key=self.end_key,
            elements=[elt.as_json() for elt in self.elements])


class ResultDict(object):

    def __init__( self ):
        self._d = {}

    def __setattr__( self, attr, value ):
        if attr == '_d':
            return object.__setattr__(self, attr, value)
        self._d[attr] = value

    def __setitem__( self, attr, value ):
        if attr == '_d':
            return object.__setattr__(self, attr, value)
        self._d[attr] = value

    def as_json( self ):
        return self._d


class Notification(object):

    def __init__( self ):
        self.updates = []  # (path, ListDiff) list

    def add_update( self, path, diff ):
        self.updates.append((path, diff))

    def as_json( self ):
        d = dict()
        if self.updates:
            d['updates'] = [(path, diff.as_json()) for path, diff in self.updates]
        return d


class Response(Notification):

    def __init__( self, request_id ):
        Notification.__init__(self)
        self.request_id = request_id
        self.object = None
        self.result = ResultDict()

    def as_json( self ):
        d = Notification.as_json(self)
        d['request_id'] = self.request_id
        if self.object:
            d['object'] = self.object
        if self.result:
            d['result'] = self.result.as_json()
        return d


class Request(object):

    def __init__( self, client, params ):
        assert isinstance(params, dict), repr(params)
        self.client = client
        self.params = params

    def __getattr__( self, name ):
        return self.params[name]

    def __getitem__( self, name ):
        return self.params[name]

    @property
    def method( self ):
        return self.params['method']

    @property
    def path( self ):
        return self.params['path']

    # request_id is included only in requests, not notifications
    def is_response_needed( self ):
        return 'request_id' in self.params

    def make_response( self ):
        return Response(self.params['request_id'])

    def make_response_object( self, obj ):
        response = self.make_response()
        response.object = obj.get()
        return response

    def make_response_result( self, **kw ):
        response = self.make_response()
        for name, value in kw.items():
            response.result[name] = value
        return response

    def make_response_update( self, path, diff ):
        assert isinstance(diff, ListDiff), repr(diff)
        response = self.make_response()
        response.add_update(path, diff)
        return response


class Object(object):

    def __init__( self, path ):
        self.path = path

    def get_path( self ):
        return self.path

    def get_commands( self ):
        return []

    def get( self ):
        return dict(
            iface_id=self.iface.id,
            view_id=self.view_id,
            path=self.get_path(),
            contents=self.get_contents(),
            )

    def get_contents( self, **kw ):
        return dict(
            commands=[cmd.as_json() for cmd in self.get_commands()],
            **kw)

    def process_request( self, request ):
        method = request['method']
        if method == 'get':
            return self.process_request_get(request)
        elif method == 'subscribe':
            self.subscribe(request)
        elif method == 'unsubscribe':
            self.unsubscribe(request)
        elif method == 'run_command':
            command_id = request['command_id']
            return self.run_command(request, command_id)
        else:
            assert False, repr(method)  # Unknown method

    def process_request_get( self, request ):
        self.subscribe(request)
        return request.make_response_result(**self.get())

    def subscribe( self, request ):
        subscription.add(self.path, request.client)

    def unsubscribe( self, request ):
        subscription.remove(self.path, request.client)

    def run_command( self, request, command_id ):
        assert False, repr(command_id)  # Unknown command


class ListObject(Object):

    def __init__( self, path ):
        Object.__init__(self, path)
        self.key_column_idx = self._pick_key_column_idx(self.get_columns())

    def _pick_key_column_idx( self, columns ):
        for idx, column in enumerate(self.get_columns()):
            if column.id == 'key':
                return idx
        assert False, 'Missing "key" column id'

    def get_contents( self, **kw ):
        elements, has_more = self.get_elements_json()
        return Object.get_contents(self,
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
            return request.make_response_result(fetched_elements = dict(
                elements=elements,
                has_more=has_more))
            return response
        elif method == 'run_element_command':
            command_id = request['command_id']
            element_key = request['element_key']
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


# return list object (base) with selected_key selected
class ListObjectElement(Object):

    def __init__( self, base, selected_key ):
        assert isinstance(base, ListObject), repr(base)
        self._base = base
        self._selected_key = selected_key

    def get( self ):
        return dict(
            iface_id=self._base.iface.id,
            view_id=self._base.view_id,
            path=self._base.get_path(),
            contents=self.get_contents(),
            )

    def get_contents( self, **kw ):
        return self._base.get_contents(
            selected_key=self._selected_key,
            **kw)
