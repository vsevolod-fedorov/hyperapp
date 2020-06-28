from collections import namedtuple

from hyperapp.client.command import command
from hyperapp.client.module import ClientModule

from . import htypes
from .column import Column
from .command_hub import CommandHub
from .simple_list_object import SimpleListObject


Item = namedtuple('Item', 'id')


async def _open_piece_do_nothing(piece):
    pass


class CommandList(SimpleListObject):

    @classmethod
    async def from_state(cls, state, ref_registry, async_ref_resolver, object_registry, object_layout_resolver):
        piece = await async_ref_resolver.resolve_ref_to_object(state.piece_ref)
        object = await object_registry.resolve_async(piece)
        command_hub = CommandHub()
        layout = await object_layout_resolver.resolve(state.layout_ref, object, command_hub, _open_piece_do_nothing)
        return cls(ref_registry, object, layout)

    def __init__(self, ref_registry, object, layout):
        super().__init__()
        self._ref_registry = ref_registry
        self._object = object
        self._layout = layout

    def get_title(self):
        return f"Commands for: {self._object.get_title()}"

    @property
    def data(self):
        piece_ref = self._ref_registry.register_object(self._object.data)
        layout_ref = self._ref_registry.register_object(self._layout.data)
        return htypes.command_list.command_list(piece_ref, layout_ref)

    def get_columns(self):
        return [
            Column('id', is_key=True),
            ]

    async def get_all_items(self):
        return [
            Item(command.id) for command
            in self._layout.collect_view_commands()
            ]


class ThisModule(ClientModule):

    def __init__(self, module_name, services):
        super().__init__(module_name, services)
        services.object_registry.register_type(
            htypes.command_list.command_list,
            CommandList.from_state,
            services.ref_registry,
            services.async_ref_resolver,
            services.object_registry,
            services.object_layout_resolver,
            )
