import asyncio
import logging
from collections import namedtuple

from hyperapp.client.command import command
from hyperapp.client.module import ClientModule

from . import htypes
from .object_command import command as object_command
from .layout_handle import LayoutWatcher
from .layout import InsertVisualItemDiff, RemoveVisualItemDiff, UpdateVisualItemDiff
from .command_hub import CommandHub
from .column import Column
from .tree_object import InsertItemDiff, RemoveItemDiff, UpdateItemDiff, TreeObject

_log = logging.getLogger(__name__)


class LayoutEditor(TreeObject):

    _CommandRec = namedtuple('_CommandRec', 'command item_path')

    def __init__(self, layout_watcher):
        super().__init__()
        self._path2item_list = {}
        self._item_commands = {}  # id -> _CommandRec
        layout_watcher.subscribe(self)

    async def _async_init(self, layout):
        root = await self.get_root_item(layout)
        self._append_item([], root)

    @property
    def columns(self):
        return [
            Column('name', is_key=True),
            Column('text'),
            ]

    def get_command(self, command_id):
        rec = self._item_commands.get(command_id)
        if rec:
            return rec.command.partial(rec.item_path)
        return super().get_command(command_id)

    def get_item_command_list(self, item_path):
        try:
            item = self._find_item(item_path)
        except KeyError:
            return []
        return item.commands or []

    def _find_item(self, item_path):
        if not item_path:
            raise KeyError(f"Empty item path {item_path}")
        item_list = self._path2item_list.get(tuple(item_path[:-1]), [])
        try:
            return next(i for i in item_list if i.name == item_path[-1])
        except StopIteration:
            raise KeyError(f"Item is missing at path {item_path}")

    async def fetch_items(self, path):
        path = tuple(path)
        item_list = self._path2item_list.get(path, [])
        for item in item_list:
            p = (*path, item.name)
            if p not in self._path2item_list:
                self._distribute_fetch_results(p, [])
        self._distribute_fetch_results(path, item_list)

    async def get_root_item(self, layout):
        return (await layout.visual_item())

    # from LayoutWatcher
    def process_layout_diffs(self, vdiff_list):
        for vdiff in vdiff_list:
            if isinstance(vdiff, InsertVisualItemDiff):
                self._insert_item(vdiff.idx, vdiff.path, vdiff.item)
                diff = InsertItemDiff(vdiff.idx, vdiff.item)
                self._distribute_diff(vdiff.path, diff)
            elif isinstance(vdiff, RemoveVisualItemDiff):
                # todo: remove item from self._path2item_list
                self._distribute_diff(vdiff.path, RemoveItemDiff())
            elif isinstance(vdiff, UpdateVisualItemDiff):
                parent_path = tuple(vdiff.path[:-1])
                item_list = self._path2item_list[parent_path]
                item_list[vdiff.path[-1]] = vdiff.item
                diff = UpdateItemDiff(vdiff.item)
                self._distribute_diff(vdiff.path, diff)
            else:
                raise RuntimeError(u"Unknown VisualItemDiff class: {vdiff}")
        self.save_changes()

    def save_changes(self):
        pass

    def _insert_item(self, idx, path, item):
        item_list = self._path2item_list.setdefault(tuple(path), [])
        item_list.insert(idx, item)
        self._add_item_commands_and_children(path, item)

    def _append_item(self, path, item):
        item_list = self._path2item_list.setdefault(tuple(path), [])
        item_list.append(item)
        self._add_item_commands_and_children(path, item)

    def _add_item_commands_and_children(self, path, item):
        item_path = (*path, item.name)
        for command in item.commands:
            self._item_commands[command.id] = self._CommandRec(command, item_path)
        for kid in item.children:
            self._append_item(item_path, kid)


class GlobalLayoutEditor(LayoutEditor):

    @classmethod
    async def from_state(cls, state, layout_manager, layout_watcher):
        # Postpone async_init because layout_manager does not have root_layout yet if we are first view on startup.
        return cls(layout_watcher, layout_manager)

    def __init__(self, layout_watcher, layout_manager):
        super().__init__(layout_watcher)
        self._layout_manager = layout_manager

    @property
    def title(self):
        return "Global view layout"

    @property
    def data(self):
        return htypes.layout_editor.view_layout_editor()

    async def fetch_items(self, path):
        if not self._path2item_list:
            # Not yet async-inited.
            await self._async_init(self._layout_manager.root_layout)
        await super().fetch_items(path)


class ObjectLayoutEditor(LayoutEditor):

    @classmethod
    async def from_state(
            cls,
            state,
            ref_registry,
            async_ref_resolver,
            object_registry,
            object_layout_association,
            object_command_layout_association,
            layout_handle_resolver,
            ):
        piece = await async_ref_resolver.resolve_ref_to_object(state.piece_ref)
        object = await object_registry.resolve_async(piece)
        layout_handle = await layout_handle_resolver.resolve(state.layout_handle_ref, object)
        self = cls(
            ref_registry,
            object_layout_association,
            object_command_layout_association,
            object,
            layout_handle,
            )
        await self._async_init(layout)
        return self

    def __init__(
            self,
            ref_registry,
            object_layout_association,
            object_command_layout_association,
            object,
            layout_handle,
            ):
        super().__init__(layout_handle.watcher)
        self._ref_registry = ref_registry
        self._object_layout_association = object_layout_association
        self._object_command_layout_association = object_command_layout_association
        self._object = object
        self._layout_handle = layout_handle

    @property
    def title(self):
        return f"Layout for category: {self._layout_handle.title}"

    @property
    def data(self):
        piece_ref = self._ref_registry.register_object(self._object.data)
        layout_handle_ref = self._ref_registry.register_object(self._layout_handle.data)
        return htypes.layout_editor.object_layout_editor(piece_ref, layout_handle_ref)

    def get_command_list(self):
        return [command for command in super().get_command_list()
                if command.id not in {'replace', '_replace_impl'}]

    async def get_root_item(self, layout):
        item = await self._layout_handle.layout.visual_item()
        return item.with_added_commands([
            self._replace_view,
            ])

    def save_changes(self):
        self._save_layout(self._layout.data)

    def _save_layout(self, layout_rec):
        layout_ref = self._ref_registry.register_object(layout_rec)
        if self._target_command:
            self._object_command_layout_association[self._target_category, self._target_command] = layout_ref
        else:
            self._object_layout_association[self._target_category] = layout_ref
        return layout_ref

    def _object_layout_editor(self, layout_ref):
        piece_ref = self._ref_registry.register_object(self._object.data)
        return htypes.layout_editor.object_layout_editor(piece_ref, layout_ref, self._target_category, command=self._target_command)

    @object_command('replace', kind='element')
    async def _replace_view(self, path):
        chooser = htypes.view_chooser.view_chooser(self._object.category_list)
        chooser_ref = self._ref_registry.register_object(chooser)
        layout_rec_maker_field = htypes.params_editor.field('layout_rec_maker', chooser_ref)
        layout_ref = self._ref_registry.register_object(self._layout.data)
        editor = self._object_layout_editor(layout_ref)
        return htypes.params_editor.params_editor(
            target_piece_ref=self._ref_registry.register_object(editor),
            target_command_id=self._replace_impl.id,
            bound_arguments=[],
            fields=[layout_rec_maker_field],
            )

    @command('_replace_impl')
    async def _replace_impl(self, layout_rec_maker):
        resource_key = self._object.hashable_resource_key
        layout_rec = await layout_rec_maker(self._object)
        layout_ref = self._save_layout(layout_rec)
        return self._object_layout_editor(layout_ref)


class ThisModule(ClientModule):

    def __init__(self, module_name, services):
        super().__init__(module_name, services)
        services.object_registry.register_type(
            htypes.layout_editor.view_layout_editor, GlobalLayoutEditor.from_state, services.layout_manager, services.layout_watcher)
        services.object_registry.register_type(
            htypes.layout_editor.object_layout_editor,
            ObjectLayoutEditor.from_state,
            services.ref_registry,
            services.async_ref_resolver,
            services.object_registry,
            services.object_layout_association,
            services.object_command_layout_association,
            services.layout_handle_resolver,
            )

    @object_command('open_view_layout')
    async def open_view_layout(self):
        return htypes.layout_editor.view_layout_editor()
