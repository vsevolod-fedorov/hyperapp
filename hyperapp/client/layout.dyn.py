import abc
import logging
import weakref
from collections import namedtuple
from dataclasses import dataclass
from typing import List

from hyperapp.client.commander import BoundCommand, Commander
from hyperapp.client.module import ClientModule

_log = logging.getLogger(__name__)


VisualItem = namedtuple('Item', 'idx name text children commands', defaults=[None, None])


@dataclass
class RootVisualItem:
    text: str
    children: List[VisualItem] = None
    commands: List[BoundCommand] = None

    def to_item(self, idx, name, commands=None):
        all_commands = (self.commands or []) + (commands or [])
        return VisualItem(idx, name, self.text, self.children, all_commands)

    def with_commands(self, commands):
        all_commands = (self.commands or []) + (commands or [])
        return RootVisualItem(self.text, self.children, all_commands)


class VisualItemDiff:
    pass


@dataclass
class InsertVisualItemDiff(VisualItemDiff):
    path: List[int]
    idx: int
    item: VisualItem


@dataclass
class RemoveVisualItemDiff(VisualItemDiff):
    path: List[int]


class LayoutWatcher:

    def __init__(self):
        self._observers = weakref.WeakSet()

    def subscribe(self, observer):
        self._observers.add(observer)

    def distribute_diffs(self, diff_list):
        _log.info("Distribute layout diffs %s to %s", diff_list, list(self._observers))
        for observer in self._observers:
            observer.process_layout_diffs(diff_list)


class Layout(Commander, metaclass=abc.ABCMeta):

    def __init__(self, path):
        super().__init__(commands_kind='view')
        self._path = path

    # todo: use abstractproperty
    @property
    def data(self):
        raise NotImplementedError(self.__class__)
    
    @abc.abstractmethod
    def get_view_ref(self):
        pass

    @abc.abstractmethod
    async def create_view(self):
        pass

    @abc.abstractmethod
    async def visual_item(self) -> VisualItem:
        pass

    def get_current_commands(self):
        return self.get_command_list({'view', 'global', 'object', 'element'})

    def collect_view_commands(self):
        return {self._path: self.get_command_list({'view'})}

    def _get_current_commands_with_child(self, child):
        # child commands should override and hide same commands from parents
        return self._merge_commands(
            child.get_current_commands(),
            Layout.get_current_commands(self),
            )

    def _merge_commands(self, primary_commands, secondary_commands):
        primary_command_ids = set(command.id for command in primary_commands)
        secondary_commands = [command for command in secondary_commands
                              if command.id not in primary_command_ids]
        return [*primary_commands, *secondary_commands]

    def _collect_view_commands_with_children(self, child_layout_it):
        children_commands = {
            path: commands
            for layout in child_layout_it
            for path, commands in layout.collect_view_commands().items()
            }
        return {
            **children_commands,
            **Layout.collect_view_commands(self),
            }
