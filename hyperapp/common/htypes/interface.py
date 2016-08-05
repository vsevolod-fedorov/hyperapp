from ..util import is_list_inst
from .htypes import (
    join_path,
    Type,
    tNone,
    tBinary,
    tString,
    TOptional,
    Field,
    TRecord,
    TList,
    tPath,
    tUrl,
    tIfaceId,
    tCommand,
    )
from .hierarchy import THierarchy
from .request import tUpdate, tClientNotificationRec, tResponseRec


tObject = THierarchy('object')
tBaseObject = tObject.register('object', fields=[Field('objimpl_id', tString)])

tProxyObject = tObject.register('proxy', base=tBaseObject, fields=[
    Field('public_key_der', tBinary),
    Field('iface', tIfaceId),
    Field('facets', TList(tIfaceId)),
    Field('path', tPath),
    ])

tProxyObjectWithContents = tObject.register('proxy_with_contents', base=tProxyObject)


tHandle = THierarchy('handle')
tViewHandle = tHandle.register('handle', fields=[Field('view_id', tString)])
tObjHandle = tHandle.register('obj_handle', base=tViewHandle, fields=[Field('object', tObject)])

tRedirectHandle = tHandle.register('redirect', fields=[Field('redirect_to', tUrl)])


class IfaceCommand(object):

    def __init__( self, command_id, params_fields=None, result_fields=None ):
        self.command_id = command_id
        self.params_fields = params_fields or []
        self.result_fields = result_fields or []

    def get_params_type( self, iface ):
        return TRecord(self.get_params_fields(iface))

    def get_result_type( self, iface ):
        return TRecord(self.get_result_fields(iface))

    def get_params_fields( self, iface ):
        return self.params_fields

    def get_result_fields( self, iface ):
        return self.result_fields


class RequestCmd(IfaceCommand):
    pass

class NotificationCmd(IfaceCommand):
    pass


class OpenCommand(RequestCmd):

    def get_result_type( self, iface ):
        return TOptional(tHandle)


class ContentsCommand(RequestCmd):

    def __init__( self, command_id, params_fields=None ):
        RequestCmd.__init__(self, command_id, params_fields)

    def get_result_type( self, iface ):
        return iface.get_contents_type()


class Interface(object):

    # client request types
    rt_request = 1
    rt_notification =2

    def __init__( self, iface_id, base=None, contents_fields=None, diff_type=tNone, commands=None ):
        assert base is None or isinstance(base, Interface), repr(base)
        assert is_list_inst(contents_fields or [], Field), repr(contents_fields)
        assert diff_type is None or isinstance(diff_type, Type), repr(diff_type)
        assert is_list_inst(commands or [], (RequestCmd, NotificationCmd)), repr(commands)
        self.iface_id = iface_id
        self.contents_fields = contents_fields or []
        self.diff_type = diff_type
        self.commands = commands or []
        if base:
            self.contents_fields = base.contents_fields + self.contents_fields
            self.commands = base.commands + self.commands
            assert diff_type is tNone, repr(diff_type)  # Inherited from base
            self.diff_type = base.diff_type
        self.id2command = dict((cmd.command_id, cmd) for cmd in self.commands + self.get_basic_commands())
        self._register_types()

    def _register_types( self ):
        self._tContents = TRecord(self.get_contents_fields())
        self._command_params_t = dict((command_id, cmd.get_params_type(self)) for command_id, cmd in self.id2command.items())
        self._command_result_t = dict((command_id, cmd.get_result_type(self)) for command_id, cmd in self.id2command.items())
        self._tObject = tObject.register(self.iface_id, base=tProxyObjectWithContents, fields=[Field('contents', self._tContents)])
        tUpdate.register((self.iface_id,), self.diff_type)
        for command in self.id2command.values():
            cmd_id = command.command_id
            tClientNotificationRec.register((self.iface_id, cmd_id), self._command_params_t[cmd_id])
            tResponseRec.register((self.iface_id, cmd_id), self._command_result_t[cmd_id])

    def get_object_type( self ):
        return self._tObject

    def get_contents_type( self ):
        return self._tContents

    def get_basic_commands( self ):
        return [
            OpenCommand('get'),
            ContentsCommand('subscribe'),
            NotificationCmd('unsubscribe'),
            ]

    def get_request_type( self, command_id ):
        assert command_id in self.id2command, repr(command_id)  # Unknown command id
        command = self.id2command[command_id]
        if isinstance(command, RequestCmd):
            return self.rt_request
        if isinstance(command, NotificationCmd):
            return self.rt_notification
        assert False, command_id  # Only RequestCmd or NotificationCmd are expected here

    def is_open_command( self, command_id ):
        return isinstance(self.id2command[command_id], OpenCommand)

    def _get_command( self, command_id ):
        cmd = self.id2command.get(command_id)
        if not cmd:
            raise TypeError('%s: Unsupported command id: %r' % (self.iface_id, command_id))
        return cmd

    def get_request_params_type( self, command_id ):
        return self._command_params_t[command_id]

    def make_params( self, command_id, *args, **kw ):
        return self.get_request_params_type(command_id)(*args, **kw)

    def get_command_result_type( self, command_id ):
        return self._command_result_t[command_id]

    def make_result( self, command_id, *args, **kw ):
        return self.get_command_result_type(command_id)(*args, **kw)

    def get_default_contents_fields( self ):
        return [Field('commands', TList(tCommand))]

    def get_contents_fields( self ):
        return self.get_default_contents_fields() + self.contents_fields

    def Object( self, **kw ):
        return self._tObject(**kw)

    def Contents( self, **kw ):
        return self._tContents(**kw)

    def Update( self, path, diff ):
        return tUpdate(self.iface_id, path, diff)
        

class IfaceRegistry(object):

    def __init__( self ):
        self.registry = {}  # iface id -> Interface

    def register( self, iface ):
        assert isinstance(iface, Interface), repr(iface)
        self.registry[iface.iface_id] = iface

    def is_registered( self, iface_id ):
        return iface_id in self.registry

    def resolve( self, iface_id ):
        return self.registry[iface_id]


iface_registry = IfaceRegistry()

def register_iface( iface ):
    iface_registry.register(iface)

def resolve_iface( iface_id ):
    return iface_registry.resolve(iface_id)


# all interfaces support this one too:        
get_iface = Interface('base_get')

register_iface(get_iface)
