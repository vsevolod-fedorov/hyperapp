import abc
import logging
import sys
import weakref
from dataclasses import dataclass, field
from collections import namedtuple
from typing import Dict, List

from .weak_key_dictionary_with_callback import WeakKeyDictionaryWithCallback
from .resource_key import module_resource_key
from .object_command import Command

log = logging.getLogger(__name__)


@dataclass
class ObjectType:
    ids: List[str]
    commands: Dict[str, 'ObjectType'] = field(default_factory=dict)


class ObjectObserver(object):

    def object_changed(self, *args, **kw):
        pass


class Object(metaclass=abc.ABCMeta):

    view_state_fields = []

    ObserverArgs = namedtuple('ObserverArgs', 'args kw')

    def __init__(self):
        self._command_list = []
        for name in dir(self):
            attr = getattr(self, name)
            if type(attr) is property:
                continue
            if not isinstance(attr, Command):
                continue
            self._command_list.append(attr)
        self._init_observers()

    @property
    def command_list(self):
        return self._command_list

    @property
    @abc.abstractmethod
    def title(self):
        pass

    @property
    @abc.abstractmethod
    def piece(self):
        pass

    @property
    def dir_list(self):
        return [[__module_ref__]]

    @classmethod
    def resource_key(cls, path=()):
        class_name = cls.__name__
        module_name = cls.__module__
        return module_resource_key(module_name, [class_name, *path])

    async def run_command(self, command_id, *args, **kw):
        command = self.get_command(command_id)
        assert command, 'Unknown command: %r; known are: %r' % (command_id, [cmd.id for cmd in self._commands])  # Unknown command
        return (await command.run(*args, **kw))

    def subscribe(self, observer, *args, **kw):
        assert isinstance(observer, ObjectObserver), repr(observer)
        log.debug('-- Object.subscribe self=%s/%s, observer=%s/%s', id(self), self, id(observer), weakref.ref(observer))
        self._on_subscriber_added()
        self._observers[observer] = self.ObserverArgs(args, kw)

    def unsubscribe(self, observer):
        log.debug('-- Object.unsubscribe; self=%s/%r, observer=%s/%s', id(self), self, id(observer), observer)
        del self._observers[observer]
        self._on_subscriber_removed()

    def observers_arrived(self):
        pass

    def observers_gone(self):
        pass

    def _init_observers(self):
        def on_remove(self_ref=weakref.ref(self)):
            self = self_ref()
            if self:
                log.debug('-- Object: observer is gone; self=%s/%r', id(self), self)
                self._on_subscriber_removed()
        self._observers = WeakKeyDictionaryWithCallback(on_remove=on_remove)

    def _on_subscriber_added(self):
        if self._observers:  # will it be first subscriber?
            return
        try:
            log.debug('-- Object.observers_arrived self=%s/%r', id(self), self)
            self.observers_arrived()
        except:
            log.exception('Error calling observers_arrived:')

    def _on_subscriber_removed(self):
        if self._observers:  # was it last subscriber?
            return
        try:
            log.debug('-- Object.observers_gone self=%s/%r', id(self), self)
            self.observers_gone()
        except:
            log.exception('Error calling observers_gone:')

    def _notify_object_changed(self, skip_observer=None):
        log.debug('-- Object._notify_object_changed, self=%s/%s observers count=%s', id(self), self, len(self._observers))
        for observer, rec in self._observers.items():
            log.debug('-- Object._notify_object_changed, observer=%s (*%s, **%s), skip=%r',
                          id(observer), rec.args, rec.kw, observer is skip_observer)
            if observer is not skip_observer:
                observer.object_changed(*rec.args, **rec.kw)
