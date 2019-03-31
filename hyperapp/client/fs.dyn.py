from collections import namedtuple
import logging

from hyperapp.common.htypes import tInt, tString, resource_key_t
from hyperapp.client.command import command
from hyperapp.client.module import ClientModule
from .async_capsule_registry import AsyncCapsuleRegistry, AsyncCapsuleResolver
from . import htypes
from .list_object import Column, ListObject

log = logging.getLogger(__name__)


MODULE_NAME = 'fs'


FetchResult = namedtuple('FetchResult', 'item_list eof')


class FsDir:

    def __init__(self, ref_registry, handle_resolver, fs_service, host):
        self._ref_registry = ref_registry
        self._handle_resolver = handle_resolver
        self._fs_service = fs_service
        self.host = host
        self._key = []
        self._path2item = {}  # cache for visited rows

    @property
    def fs_service_ref(self):
        return self._fs_service.to_ref()

    def get_command_list(self, kinds):
        command_list = ListObject.get_command_list(self, kinds)
        if not self._path:
            return [command for command in command_list if command.id != 'open_parent']
        else:
            return command_list

    # def pick_current_refs(self):
    #     return [self._get_path_ref(self._path)]

    def get_columns(self):
        return [
            Column('key', is_key=True),
            Column('ftype'),
            Column('ftime', type=tInt),
            Column('fsize', type=tInt),
            ]

    async def fetch_items(self, path, from_key):
        chunk = await self._fs_service.fetch_dir_contents(
            self.host, list(path),
            sort_column_id='key',
            from_key=from_key,
            desc_count=0,
            asc_count=50,
            )
        self._path2item.update({tuple(path) + (row.key,): row for row in chunk.rows})
        return FetchResult(
            item_list=chunk.rows,
            eof=chunk.eof,
            )

    # def process_diff(self, diff):
    #     assert isinstance(diff, ListDiff), repr(diff)
    #     log.info('-- FsDirObject.process_diff self=%r diff=%r', id(self), diff)

    # def get_element_command_list(self, element_key):
    #     all_command_list = ListObject.get_element_command_list(self, element_key)
    #     row = self._key2item[element_key]
    #     if row.ftype == 'dir':
    #         return all_command_list
    #     else:
    #         return [command for command in all_command_list if command.id != 'open']

    # def _get_path_ref(self, path, current_file_name=None):
    #     fs_service_ref = self._fs_service.to_ref()
    #     object = htypes.fs.fs(fs_service_ref, self._host, path, current_file_name)
    #     return self._ref_registry.register_object(object)

    # async def _open_path(self, path, current_file_name=None):
    #     ref = self._get_path_ref(path, current_file_name)
    #     return (await self._handle_resolver.resolve(ref))

    # @command('open', kind='element')
    # async def command_open(self, element_key):
    #     path = self._path + [element_key]
    #     return (await self._open_path(path))

    # @command('open_parent')
    # async def command_open_parent(self):
    #     if len(self._path) > 0:
    #         path = self._path[:-1]
    #         return (await self._open_path(path, current_file_name=self._path[-1]))


class ListAdapter(ListObject):

    impl_id = 'fs_dir_list'

    @classmethod
    async def from_state(cls, state, ref_registry, handle_resolver, fs_service_resolver):
        fs_service = await fs_service_resolver.resolve(state.fs_service_ref)
        dir = FsDir(ref_registry, handle_resolver, fs_service, state.host)
        return cls(dir, state.path)

    def __init__(self, dir, path):
        ListObject.__init__(self)
        self._dir = dir
        self._path = path

    def get_title(self):
        return '%s:/%s' % (self._dir.host, '/'.join(self._path))

    def get_state(self):
        return htypes.fs.fs_dir_object(self.impl_id, self._dir.fs_service_ref, self._dir.host, self._path)

    def get_columns(self):
        return self._dir.get_columns()

    async def fetch_items(self, from_key):
        result = await self._dir.fetch_items(self._path, from_key)
        self._distribute_fetch_results(result.item_list)
        if result.eof:
            self._distribute_eof()


class ThisModule(ClientModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME, services)
        services.fs_service_registry = fs_service_registry = AsyncCapsuleRegistry('fs_service', services.type_resolver)
        services.fs_service_resolver = fs_service_resolver = AsyncCapsuleResolver(services.async_ref_resolver, fs_service_registry)
        services.handle_registry.register_type(htypes.fs.fs, self._resolve_fs)
        services.objimpl_registry.register(
            ListAdapter.impl_id, ListAdapter.from_state, services.ref_registry, services.handle_resolver, fs_service_resolver)

    async def _resolve_fs(self, fs_ref, fs):
        dir_object = htypes.fs.fs_dir_object(ListAdapter.impl_id, fs.fs_service_ref, fs.host, fs.path)
        handle_t = htypes.core.string_list_handle
        sort_column_id = 'key'
        resource_key = resource_key_t(__module_ref__, ['FsDir'])
        list_handle = handle_t('list', dir_object, resource_key, key=fs.current_file_name)
        return list_handle
        # filter_object = htypes.line_object.line_object('line', '')
        # filter_view = htypes.line_object.line_edit_view('line_edit', filter_object, mode='edit')
        # narrower_object = htypes.narrower.narrower_object('narrower', filtered_field='key')
        # narrower_view = htypes.narrower.narrower_view('narrower', narrower_object, filter_view, list_handle)
        # return narrower_view
