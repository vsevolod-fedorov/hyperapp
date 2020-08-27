import abc
import logging
from collections import namedtuple
from dataclasses import dataclass
from typing import List

from hyperapp.client.commander import BoundCommand, Commander

from . import htypes
from .items_view import map_columns_to_view
from .layout_command import LayoutCommand

_log = logging.getLogger(__name__)


@dataclass
class VisualItem:
    name: str
    text: str
    children: List['VisualItem'] = None
    commands: List[BoundCommand] = None

    def with_added_commands(self, commands_it):
        all_commands = [*self.commands, *commands_it]
        return VisualItem(self.name, self.text, self.children, all_commands)


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


@dataclass
class UpdateVisualItemDiff(VisualItemDiff):
    path: List[int]
    item: VisualItem


class Layout(Commander, metaclass=abc.ABCMeta):

    def __init__(self, path):
        super().__init__(commands_kind='view')
        self._path = path

    # todo: use abstractproperty
    @property
    def data(self):
        raise NotImplementedError(self.__class__)

    @abc.abstractmethod
    async def create_view(self):
        pass

    @abc.abstractmethod
    async def visual_item(self) -> VisualItem:
        pass

    def collect_view_commands(self):
        return [(tuple(self._path), command)
                for command in self.get_command_list({'view'})
                ]

    def make_visual_item(self, text, name=None, children=None, commands=None):
        if not name:
            name = self._path[-1]
        return VisualItem(name, text, children or [], commands or [])

    def _merge_commands(self, primary_commands, secondary_commands):
        primary_command_ids = set(command.id for command in primary_commands)
        secondary_commands = [command for command in secondary_commands
                              if command.id not in primary_command_ids]
        return [*primary_commands, *secondary_commands]

    def _collect_view_commands_with_children(self, child_layout_it):
        children_commands = [
            (path, command)
            for layout in child_layout_it
            for path, command in layout.collect_view_commands()
            ]
        return [
            *children_commands,
            *Layout.collect_view_commands(self),
            ]


class GlobalLayout(Layout):

    def get_current_commands(self):
        return self.get_all_command_list()

    def _get_current_commands_with_child(self, child):
        # child commands should override and hide same commands from parents
        return self._merge_commands(
            child.get_current_commands(),
            GlobalLayout.get_current_commands(self),
            )


class ObjectLayout(Layout):

    def __init__(self, path, object, command_list_data):
        super().__init__(path)
        self._object = object
        self._id_to_code_command = {
            command.id: (path, command)
            for path, command in self.collect_view_commands()
            }
        self._command_list = []
        for command in command_list_data:
            path, code_command = self._id_to_code_command[command.code_id]
            self.command_list.append(LayoutCommand(command.id, code_command, path, command.layout_ref))

    def get_current_commands(self, view):
        return self.get_all_command_list()

    def collect_view_commands(self):
        return [
            *super().collect_view_commands(),
            *[(tuple(self._path), command) for command in self._object.get_all_command_list()],
            ]

    @property
    def command_list(self):
        return self._command_list

    def add_command(self, id, code_id):
        path, code_command = self._id_to_code_command[code_id]
        command = LayoutCommand(id, code_command, path, layout_ref=None)
        self._command_list.append(command)

    @property
    def _command_list_data(self):
        return [
            htypes.layout.command(command.id, command.code_command.id, command.layout_ref)
            for command in self.command_list
            ]


class MultiItemObjectLayout(ObjectLayout, metaclass=abc.ABCMeta):

    class _CurrentItemObserver:

        def __init__(self, layout, command_hub):
            self._layout = layout
            self._command_hub = command_hub

        def current_changed(self, current_item_key):
            self._command_hub.update(only_kind='element')

    def __init__(self, path, object, command_list_data, resource_resolver):
        super().__init__(path, object, command_list_data)
        self._resource_resolver = resource_resolver
        self._current_item_observer = None

    async def create_view(self, command_hub):
        columns = list(map_columns_to_view(self._resource_resolver, self._object))
        view = self._create_view_impl(columns)
        self._current_item_observer = observer = self._CurrentItemObserver(self, command_hub)
        view.add_observer(observer)
        return view

    @abc.abstractmethod
    def _create_view_impl(self, columns):
        pass

    def get_current_commands(self, view):
        command_list = [command for command in self._command_list
                        if command.kind != 'element']
        current_item_key = view.current_item_key
        if current_item_key is None:
            return command_list
        element_command_ids = {
            command.id for command in
            self._object.get_item_command_list(current_item_key)
            }
        element_command_list = [
            command.partial(current_item_key)
            for command in self._command_list
            if command.kind == 'element' and command.id in element_command_ids
            ]
        return [*command_list, *element_command_list]
