from abc import ABCMeta, abstractmethod
import asyncio
import logging

from PySide2 import QtCore, QtWidgets

from hyperapp.client.module import ClientModule

from . import htypes
from .object_command import command
from .composite import Composite
from .layout import RootVisualItem, VisualItem, ObjectLayout
from .list_object import ListObject
from .tree_object import TreeObject
from .view_chooser import LayoutRecMakerField

_log = logging.getLogger(__name__)


class MasterDetailsView(QtWidgets.QSplitter, Composite):

    def __init__(self, object_registry, object_layout_producer, command_hub, master_view, details_command_id, sizes=None):
        QtWidgets.QSplitter.__init__(self, QtCore.Qt.Vertical)
        Composite.__init__(self, children=[master_view])
        self._object_registry = object_registry
        self._object_layout_producer = object_layout_producer
        self._command_hub = command_hub
        self._master_view = master_view
        self._details_command_id = details_command_id
        self._want_sizes = sizes
        master_view.set_parent(self)
        self.insertWidget(0, master_view)
        master_view.add_observer(self)

    def setVisible(self, visible):
        QtWidgets.QSplitter.setVisible(self, visible)
        if visible:
            self.widget(0).setFocus()

    def get_current_child(self):
        return self._master_view

    def current_changed(self, current_key):
        asyncio.ensure_future(self._update_details(current_key))

    async def _update_details(self, current_key):
        if self.count() > 1:
            w = self.widget(1)
            w.setParent(None)
            w.deleteLater()
        master_object = self._master_view.get_object()
        try:
            details_command = master_object.get_command(self._details_command_id)
        except KeyError:
            _log.warning("Master %s does not has command %r", master_object, self._details_command_id)
            return
        _log.info('Run command to open details: %r', details_command.id)
        resolved_piece = await details_command.run(current_key)
        if not resolved_piece:
            return
        view = await resolved_piece.layout.create_view(self._command_hub)
        self.insertWidget(1, view)
        if self._want_sizes:
            self.setSizes(self._want_sizes)
            self._want_sizes = None


class MasterDetailsLayout(ObjectLayout):

    @classmethod
    async def from_data(cls, state, object, ref_registry, object_registry, object_layout_resolver, object_layout_producer):
        return cls(
            ref_registry, object_registry, object_layout_resolver, object_layout_producer,
            state.master_layout_ref, state.command_id, object, [])

    def __init__(self, ref_registry, object_registry, object_layout_resolver, object_layout_producer,
                 master_layout_ref, command_id, object, path):
        super().__init__(path)
        self._ref_registry = ref_registry
        self._object_registry = object_registry
        self._object_layout_resolver = object_layout_resolver
        self._object_layout_producer = object_layout_producer
        self._details_command_id = command_id
        self._master_layout_ref = master_layout_ref
        self._command_id = command_id
        self._object = object

    @property
    def data(self):
        return htypes.master_details.master_details_layout(
            master_layout_ref=self._master_layout_ref,
            command_id=self._details_command_id,
            )

    async def create_view(self, command_hub):
        master_layout = await self._create_master_layout()
        master_view = await master_layout.create_view(command_hub)
        return MasterDetailsView(
            self._object_registry, self._object_layout_producer,
            command_hub, master_view, self._details_command_id)

    async def visual_item(self):
        master_layout = await self._create_master_layout()
        master_item = await master_layout.visual_item()
        return RootVisualItem('MasterDetails', children=[
            master_item.to_item(0, 'master', commands=[self._replace_view]),
            VisualItem(1, 'command', str(self._details_command_id)),
            ])

    async def _create_master_layout(self):
        return (await self._object_layout_resolver.resolve(self._master_layout_ref, self._object))

    @command('replace')
    async def _replace_view(self, path, view: LayoutRecMakerField):
        resource_key = self._object.hashable_resource_key
        self._object_layout_overrides[resource_key] = self._reg_registry.register_object(self.data)  # todo
        piece_ref = self._ref_registry.register_object(self._piece)
        return htypes.layout_editor.object_layout_editor(piece_ref)


class ThisModule(ClientModule):

    def __init__(self, module_name, services):
        super().__init__(module_name, services)
        self._ref_registry = services.ref_registry
        self._default_object_layouts = services.default_object_layouts
        category_list = [*ListObject.category_list, *TreeObject.category_list]
        services.available_object_layouts.register('master_details', category_list, self._make_master_detail_layout_rec)
        services.object_layout_registry.register_type(
            htypes.master_details.master_details_layout,
            MasterDetailsLayout.from_data,
            services.ref_registry,
            services.object_registry,
            services.object_layout_resolver,
            services.object_layout_producer,
            )

    async def _make_master_detail_layout_rec(self, object):
        rec_it = self._default_object_layouts.resolve(object.category_list)
        try:
            rec = next(rec_it)
        except StopIteration:
            raise RuntimeError(f"At least one default category is expected for {object} categoriees: {object.category_list}.")
        master_layout_rec = await rec.layout_rec_maker(object)
        master_layout_ref = self._ref_registry.register_object(master_layout_rec)
        return htypes.master_details.master_details_layout(
            master_layout_ref=master_layout_ref,
            command_id='open',
            )
