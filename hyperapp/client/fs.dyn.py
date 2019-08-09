from collections import namedtuple
import logging

from hyperapp.common.htypes import tInt, tString, resource_key_t
from hyperapp.client.command import command
from hyperapp.client.module import ClientModule
from .async_capsule_registry import AsyncCapsuleRegistry, AsyncCapsuleResolver
from . import htypes
from .column import Column
from .list_object import ListObject

log = logging.getLogger(__name__)


FetchResult = namedtuple('FetchResult', 'item_list eof')


class FsDir:

    def __init__(self, ref_registry, fs_service, host):
        self._ref_registry = ref_registry
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

    async def fetch_items(self, path, from_key=None):
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

    def get_item(self, path):
        return self._path2item.get(tuple(path))

    def get_fs(self, path, current_file_name=None):
        return htypes.fs.fs(self.fs_service_ref, self.host, path, current_file_name)

    # def process_diff(self, diff):
    #     assert isinstance(diff, ListDiff), repr(diff)
    #     log.info('-- FsDirObject.process_diff self=%r diff=%r', id(self), diff)


class FsDirListAdapter(ListObject):

    @classmethod
    async def from_state(cls, state, ref_registry, fs_service_resolver):
        fs_service = await fs_service_resolver.resolve(state.fs_service_ref)
        dir = FsDir(ref_registry, fs_service, state.host)
        return cls(dir, state.path)

    def __init__(self, dir, path):
        self._dir = dir
        self._path = path
        super().__init__()

    def get_title(self):
        return '%s:/%s' % (self._dir.host, '/'.join(self._path))

    def get_state(self):
        return htypes.fs.fs_dir_list(self.impl_id, self._dir.fs_service_ref, self._dir.host, self._path)

    def get_columns(self):
        return self._dir.get_columns()

    async def fetch_items(self, from_key):
        result = await self._dir.fetch_items(self._path, from_key)
        self._distribute_fetch_results(result.item_list)
        if result.eof:
            self._distribute_eof()

    def get_item_command_list(self, item_id):
        all_command_list = super().get_item_command_list(item_id)
        item = self._dir.get_item(self._path + [item_id])
        if item and item.ftype == 'dir':
            return all_command_list
        else:
            return [command for command in all_command_list if command.id != 'open']

    @command('open', kind='element')
    async def command_open(self, item_id):
        path = self._path + [item_id]
        return (await self._open_path(path))

    @command('open_parent')
    async def command_open_parent(self):
        if not self._path:
            return
        path = self._path[:-1]
        return (await self._open_path(path, current_file_name=self._path[-1]))

    async def _open_path(self, path, current_file_name=None):
        return self._dir.get_fs(path, current_file_name)


class ThisModule(ClientModule):

    def __init__(self, module_name, services):
        super().__init__(module_name, services)
        services.fs_service_registry = fs_service_registry = AsyncCapsuleRegistry('fs_service', services.type_resolver)
        services.fs_service_resolver = fs_service_resolver = AsyncCapsuleResolver(services.async_ref_resolver, fs_service_registry)
        services.object_registry.register_type(
            htypes.fs.fs, FsDirListAdapter.from_state, services.ref_registry, fs_service_resolver)
