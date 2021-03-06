# code repository proxy

import os
import logging
import uuid
from PySide2 import QtCore, QtWidgets
from ..common.htypes import (
    tString,
    Column,
    list_handle_type,
    )
from ..common.interface import packet as packet_types
from ..common.interface import core as core_types
from ..common.interface import code_repository as code_repository_types
from ..common.interface import form as form_types
from ..common.url import Url
from .module import ClientModule
from .request import Request
from .server import Server
from .proxy_object import ProxyObject
from .command import command
from .object import Object
from .list_object import Element, Chunk, ListObject
#from .form import formHandle
from .named_url_file_repository import NamedUrl, NamedUrlRepository, FileNamedUrlRepository

log = logging.getLogger(__name__)


class CodeRepository(object):

    def __init__(self, iface_registry, remoting, cache_repository, url_repository):
        assert isinstance(url_repository, NamedUrlRepository), repr(url_repository)
        self._iface_registry = iface_registry
        self._remoting = remoting
        self._cache_repository = cache_repository
        self._url_repository = url_repository
        self._items = list(self._url_repository.enumerate())  # NamedUrl list

    def set_url_repository(self, url_repository):
        self._url_repository = url_repository

    def get_items(self):
        return self._items

    def add(self, name, url):
        assert url.iface is code_repository_types.code_repository, repr(url.iface.iface_id)
        id = str(uuid.uuid4())
        item = NamedUrl(id, name, url)
        self._items.append(item)
        self._url_repository.add(item)
        return item

    # todo: try all items
    async def get_modules_by_ids(self, module_ids):
        if not self._items:
            return (None, None, None)
        proxy = CodeRepositoryProxy.from_url(self._iface_registry, self._remoting, self._cache_repository, self._items[0].url)
        return (await proxy.get_modules_by_ids(module_ids))

    # todo: try all items
    async def get_modules_by_requirements(self, requirements):
        if not self._items:
            log.warn('No available code repository servers are found')
            return (None, None, None)
        proxy = CodeRepositoryProxy.from_url(self._iface_registry, self._remoting, self._cache_repository, self._items[0].url)
        return (await proxy.get_modules_by_requirements(requirements))


class CodeRepositoryProxy(ProxyObject):

    @classmethod
    def from_url(cls, iface_registry, remoting, cache_repository, url):
        assert isinstance(url, Url), repr(url)
        server = Server.from_public_key(remoting, url.public_key)
        return cls(packet_types, core_types, iface_registry, cache_repository,
                   this_module.resources_manager, this_module.param_editor_registry, server, url.path, url.iface)
        
    def __init__( self, packet_types, core_types, iface_registry, cache_repository,
                  resources_manager, param_editor_registry, server, path, iface, facets=None ):
        assert iface is code_repository_types.code_repository, repr(iface.iface_id)
        ProxyObject.__init__(self, packet_types, core_types, iface_registry, cache_repository,
                             resources_manager, param_editor_registry, server, path, iface, facets)

    async def get_modules_by_ids(self, module_ids):
        result = await self.execute_request('get_modules_by_ids', module_ids=module_ids)
        return (result.type_modules, result.code_modules, result.resources)

    async def get_modules_by_requirements(self, requirements):
        result = await self.execute_request('get_modules_by_requirements', requirements=requirements)
        return (result.type_modules, result.code_modules, result.resources)


tFormObject = core_types.object.register('code_repository_form', base=core_types.object_base)

class CodeRepositoryFormObject(Object):

    @classmethod
    def from_state(cls, state, iface_registry, code_repository):
        return cls(iface_registry, code_repository)

    def __init__(self, iface_registry, code_repository):
        assert isinstance(code_repository, CodeRepository), repr(code_repository)
        Object.__init__(self)
        self.iface_registry = iface_registry
        self.code_repository = code_repository

    @staticmethod
    def get_state():
        return tFormObject('code_repository_form')

    @property
    def title(self):
        return 'Add code repository'

    @command('submit')
    def command_submit(self, name, url):
        log.info('adding code repository %r...', name)
        url_ = Url.from_str(self.iface_registry, url)
        item = self.code_repository.add(name, url_)
        log.info('adding code repository %r, id=%r: done', item.name, item.id)
        return make_code_repository_list(name)


def make_code_repository_form(url_str):
    object = CodeRepositoryFormObject.get_state()
    return formHandle(object, [
        form_types.form_field('name', form_types.string_field_handle('string', 'default repository')),
        form_types.form_field('url', form_types.string_field_handle('string', url_str)),
        ])


code_repository_list_type = core_types.object_base
code_repository_list_handle_type = list_handle_type(core_types, tString)


class CodeRepositoryList(ListObject):

    @classmethod
    def from_state(cls, state, code_repository):
        return cls(code_repository)
    
    def __init__(self, code_repository):
        assert isinstance(code_repository, CodeRepository), repr(code_repository)
        ListObject.__init__(self)
        self.code_repository = code_repository

    @staticmethod
    def get_state():
        return code_repository_list_type('code_repository_list')

    @property
    def title(self):
        return 'Code repository list'

    @command('add')
    def command_add(self):
        url_str = QtWidgets.QApplication.clipboard().text()
        return make_code_repository_form(url_str)

    @property
    def columns(self):
        return [Column('name')]

    def get_key_column_id(self):
        return 'name'

    async def fetch_elements_impl(self, sort_column_id, key, desc_count, asc_count):
        items = self.code_repository.get_items()
        return Chunk('name', None, list(map(self._item2element, items)), bof=True, eof=True)

    def _item2element(self, item):
        assert isinstance(item, NamedUrl), repr(item)
        return Element(item.name, item, commands=[])


def make_code_repository_list(key=None):
    object = CodeRepositoryList.get_state()
    return code_repository_list_handle_type('list', object, ['client_module', 'code_repository', 'CodeRepositoryList'], sort_column_id='name', key=key)


class ThisModule(ClientModule):

    def __init__(self, services):
        super().__init__(services)
        self.resources_manager = services.resources_manager
        self.param_editor_registry = services.param_editor_registry
        services.code_repository = CodeRepository(
            services.iface_registry, services.remoting, services.cache_repository,
            FileNamedUrlRepository(services.iface_registry, os.path.expanduser('~/.local/share/hyperapp/client/code_repositories')))
        services.objimpl_registry.register('code_repository_form', CodeRepositoryFormObject.from_state, services.iface_registry, services.code_repository)
        services.objimpl_registry.register('code_repository_list', CodeRepositoryList.from_state, services.code_repository)

    @command('repository_list')
    def command_repository_list(self):
        return make_code_repository_list()

    def get_object_command_list(self, object, kinds=None):
        if code_repository_types.code_repository in object.get_facets():
            return [self.object_command_add_to_repository_list]
        return []

    @command('add_to_repository_list', kind='object')
    def object_command_add_to_repository_list(self, object):
        assert code_repository_types.code_repository in object.get_facets()
        url = object.get_url().clone(iface=code_repository_types.code_repository)
        return make_code_repository_form(url.to_str())
