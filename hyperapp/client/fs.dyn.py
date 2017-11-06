import asyncio
from ..common.htypes import tInt, tString, Column, list_handle_type
from ..common.url import Url
from ..common.interface import core as core_types
from ..common.interface import hyper_ref as href_types
from ..common.interface import fs as fs_types
from ..common.list_object import Element, Chunk
from .module import Module
from .list_object import ListObject


class FsDirObject(ListObject):

    objimpl_id = 'fs_dir'

    @classmethod
    def from_state(cls, state, service_registry):
        fs_service = service_registry.resolve(state.fs_service)
        return cls(fs_service, state.host, state.path)

    def __init__(self, fs_service, host, path):
        ListObject.__init__(self)
        self._fs_service = fs_service
        self._host = host
        self._path = path

    def get_state(self):
        return fs_types.fs_dir_object(self.objimpl_id, self._fs_service.to_data(), self._host, self._path)

    def get_title(self):
        return '%s:%s' % (self._host, '/'.join(self._path))

    def get_commands(self):
        return ListObject.get_commands(self)

    def get_columns(self):
        return [
            Column('key', is_key=True),
            Column('ftype'),
            Column('ftime', type=tInt),
            Column('fsize', type=tInt),
            ]

    def get_key_column_id(self):
        return 'key'

    @asyncio.coroutine
    def fetch_elements(self, sort_column_id, from_key, desc_count, asc_count):
        chunk = yield from self._fs_service.fetch_dir_contents(
            self._host, self._path, sort_column_id, from_key, desc_count, asc_count)
        elements = [Element(row.key, row, commands=None, order_key=getattr(row, sort_column_id))
                    for row in chunk.rows]
        list_chunk = Chunk(sort_column_id, from_key, elements, chunk.bof, chunk.eof)
        self._notify_fetch_result(list_chunk)
        return list_chunk

    def process_diff(self, diff):
        assert isinstance(diff, ListDiff), repr(diff)
        log.info('-- FsDirObject.process_diff self=%r diff=%r', id(self), diff)


class FsService(object):

    @classmethod
    def from_data(cls, service_object, iface_registry, proxy_factory):
        service_url = Url.from_data(iface_registry, service_object.service_url)
        service_proxy = proxy_factory.from_url(service_url)
        return cls(service_proxy)

    def __init__(self, service_proxy):
        self._service_proxy = service_proxy

    def to_data(self):
        service_url = self._service_proxy.get_url()
        return href_types.fs_service(service_url.to_data())

    @asyncio.coroutine
    def fetch_dir_contents(self, host, path, sort_column_id, from_key, desc_count, asc_count):
        fetch_request = fs_types.row_fetch_request(sort_column_id, from_key, desc_count, asc_count)
        result = yield from self._service_proxy.fetch_dir_contents(host, path, fetch_request)
        return result.chunk


class ThisModule(Module):

    def __init__(self, services):
        Module.__init__(self, services)
        self._href_resolver = services.href_resolver
        self._service_registry = services.service_registry
        services.href_object_registry.register(href_types.fs_ref.id, self.resolve_fs_object)
        services.service_registry.register(href_types.fs_service.id, FsService.from_data, services.iface_registry, services.proxy_factory)
        services.objimpl_registry.register(FsDirObject.objimpl_id, FsDirObject.from_state, services.service_registry)

    @asyncio.coroutine
    def resolve_fs_object(self, fs_object):
        fs_service_object = yield from self._href_resolver.resolve_service_ref(fs_object.fs_service_ref)
        dir_object = fs_types.fs_dir_object(FsDirObject.objimpl_id, fs_service_object, fs_object.host, fs_object.path)
        handle_t = list_handle_type(core_types, tString)
        sort_column_id = 'key'
        resource_id = ['interface', fs_types.fs_dir.iface_id]
        return handle_t('list', dir_object, resource_id, sort_column_id, None)
