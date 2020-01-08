import logging
import inspect
import weakref
import abc

from ..common.util import is_list_inst
from ..common.htypes import resource_key_t

_log = logging.getLogger(__name__)


# returned from Object.get_commands
class Command(metaclass=abc.ABCMeta):

    def __init__(self, id, kind, resource_key, enabled=True):
        assert isinstance(kind, str), repr(kind)
        assert isinstance(resource_key, resource_key_t), repr(resource_key)
        assert isinstance(enabled, bool), repr(enabled)
        self.id = id
        self.kind = kind
        self.resource_key = resource_key
        self.enabled = enabled

    def __repr__(self):
        return '%s(id=%r kind=%r)' % (self.__class__.__name__, self.id, self.kind)

    def is_enabled(self):
        return self.enabled

    def set_enabled(self, enabled):
        if enabled == self.enabled: return
        self.enabled = enabled
        object = self.get_view()
        _log.debug('-- Command.set_enabled %r object=%r', self.id, object)
        if object:
            object._notify_object_changed()

    def enable(self):
        self.set_enabled(True)

    def disable(self):
        self.set_enabled(False)
    
    @abc.abstractmethod
    async def run(self, *args, **kw):
        pass


class BoundCommand(Command):

    def __init__(self, id, kind, resource_key, enabled, class_method, inst_wr, args=None, kw=None):
        Command.__init__(self, id, kind, resource_key, enabled)
        self._class_method = class_method
        self._inst_wr = inst_wr  # weak ref to class instance
        self._args = args or ()
        self._kw = kw or {}

    def __repr__(self):
        return 'BoundCommand(%r/%r -> %r, (%r, %r))' % (self.id, self.kind, self._inst_wr, self._args, self._kw)

    def get_view(self):
        return self._inst_wr()

    async def run(self, *args, **kw):
        inst = self._inst_wr()
        if not inst:
            return  # instance we bound to is already deleted
        _log.info('BoundCommand.run: %s, %r/%r, %r, (%s+%s, %s+%s)', self, self.id, self.kind, inst, self._args, args, self._kw, kw)
        if inspect.iscoroutinefunction(self._class_method):
            return (await self._class_method(inst, *self._args, *args, **self._kw, **kw))
        else:
            return self._class_method(inst, *self._args, *args, **self._kw, **kw)

    def wrap(self, wrapper):
        async def fn(*args, **kw):
            result = await self.run(*args, **kw)
            return (await wrapper(result))
        return FreeFnCommand(self.id, self.kind, self.resource_key, self.enabled, fn)

    def partial(self, *args, **kw):
        return BoundCommand(self.id, self.kind, self.resource_key, self.enabled, self._class_method, self._inst_wr,
                            (*self._args, *args), {**self._kw, **kw})

    def bound_arguments(self, *args, **kw):
        signature = inspect.signature(self._class_method)
        inst = self._inst_wr()
        assert inst  # instance we bound to is already deleted
        return signature.bind_partial(self, *args, **kw)

    def more_params_are_required(self, *args, **kw):
        signature = inspect.signature(self._class_method)
        try:
            self = None
            signature.bind(self, *args, **kw)
            return False
        except TypeError as x:
            if str(x).startswith('missing a required argument: '):
                _log.info("More params are required: %s", x)
                return True
            else:
                raise


class FreeFnCommand(Command):

    @classmethod
    def from_command(cls, command, fn):
        return cls(command.id, command.kind, command.resource_key, command.enabled, fn)

    def __init__(self, id, kind, resource_key, enabled, fn, args=None, kw=None):
        Command.__init__(self, id, kind, resource_key, enabled)
        self._fn = fn
        self._args = args or ()
        self._kw = kw or {}

    def __repr__(self):
        return 'FreeFnCommand(%r/%r -> %r (%r, %r))' % (self.id, self.kind, self._fn, self._args, self._kw)

    async def run(self, *args, **kw):
        _log.info('FreefnCommand.run: %s, %r/%r, (%s+%s, %s+%s)', self, self.id, self.kind, self._args, args, self._kw, kw)
        return (await self._fn(*self._args, *args, **self._kw, **kw))

    def more_params_are_required(self, *args, **kw):
        return False


class UnboundCommand(object):

    def __init__(self, id, kind, resource_key, enabled, class_method):
        assert isinstance(id, str), repr(id)
        assert kind is None or isinstance(kind, str), repr(kind)
        assert isinstance(resource_key, resource_key_t), repr(resource_key)
        assert isinstance(enabled, bool), repr(enabled)
        self.id = id
        self.kind = kind
        self._resource_key = resource_key
        self.enabled = enabled
        self._class_method = class_method

    def bind(self, inst, kind):
        if self.kind is not None:
            kind = self.kind
        return self._bind(weakref.ref(inst), kind)

    def _bind(self, inst_wr, kind):
        return BoundCommand(self.id, kind, self._resource_key, self.enabled, self._class_method, inst_wr)


class Commander(object):

    def __init__(self, commands_kind):
        if hasattr(self, '_commands'):  # multiple inheritance hack
            return  # do not populate _commands twice
        self._commands_kind = commands_kind
        self._commands = []  # BoundCommand list
        for name in dir(self):
            cls = type(self)
            if hasattr(cls, name) and type(getattr(cls, name)) is property:
                continue  # avoid to call properties as we are not yet fully constructed
            attr = getattr(self, name)
            if not isinstance(attr, UnboundCommand): continue
            bound_cmd = attr.bind(self, commands_kind)
            setattr(self, name, bound_cmd)  # set_enabled must change command for this view, not for all of them
            self._commands.append(bound_cmd)

    def get_command(self, command_id):
        for command in self._commands:
            assert isinstance(command, BoundCommand), repr(command)
            if command.id == command_id:
                return command
        raise KeyError("Unknown command: {!r}".format(command_id))

    def get_command_list(self, kinds=None):
        if kinds is None:
            kinds = {self._commands_kind}
        return [cmd for cmd in self.get_all_command_list() if cmd.kind in kinds]

    def get_all_command_list(self):
        return self._commands
