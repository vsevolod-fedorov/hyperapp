# code repository proxy

import os.path
import glob
import uuid
from ..common.htypes import (
    tString,
    Field,
    TRecord,
    tUrl,
    tObject,
    tBaseObject,
    IfaceRegistry,
    iface_registry,
    Column,
    list_handle_type,
    )
from ..common.interface.code_repository import code_repository_iface
from ..common.endpoint import Url
from ..common.packet_coders import packet_coders
from .request import Request
from .server import Server
from .objimpl_registry import objimpl_registry
from .proxy_object import ProxyObject
from .command import Command
from .list_object import Element, Slice, ListObject
from .import form_view
from . import list_view


class Item(object):

    type = TRecord([
        Field('name', tString),
        Field('url', tUrl),
        ])

    @classmethod
    def from_data( cls, iface_registry, id, rec ):
        assert isinstance(rec, cls.type), repr(rec)
        return cls(id, rec.name, Url.from_data(iface_registry, rec.url))

    def __init__( self, id, name, url ):
        assert isinstance(id, unicode), repr(id)
        assert isinstance(name, unicode), repr(name)
        assert isinstance(url, Url), repr(url)
        self.id = id
        self.name = name
        self.url = url

    def to_data( self ):
        return self.type(self.name, self.url.to_data())


class FileUrlRepository(object):

    fext = '.url'
    encoding = 'json_pretty'

    def __init__( self, iface_registry, dir ):
        assert isinstance(iface_registry, IfaceRegistry), repr(iface_registry)
        self.iface_registry = iface_registry
        self.dir = dir

    def enumerate( self ):
        for fpath in glob.glob(os.path.join(self.dir, '*' + self.fext)):
            yield self._load_item(fpath)

    def add( self, item ):
        assert isinstance(item, Item), repr(item)
        self._save_item(item)

    def _load_item( self, fpath ):
        fname = os.path.basename(fpath)
        name, ext = os.path.splitext(fname)  # file name is Item.id
        with open(fpath) as f:
            data = f.read()
        rec = packet_coders.decode(self.encoding, data, Item.type)
        return Item.from_data(name, self.iface_registry, rec)

    def _save_item( self, item ):
        if not os.path.isdir(self.dir):
            os.makedirs(self.dir)
        data = packet_coders.encode(self.encoding, item.to_data(), Item.type)
        fpath = os.path.join(self.dir, item.id + self.fext)
        with open(fpath, 'w') as f:
            f.write(data)


class CodeRepositoryController(object):

    def __init__( self, url_repository ):
        assert isinstance(url_repository, FileUrlRepository), repr(url_repository)
        self._url_repository = url_repository
        self._items = list(self._url_repository.enumerate())  # Item list

    def get_items( self ):
        return self._items

    def add( self, name, url ):
        id = str(uuid.uuid4())
        item = Item(id, name, url)
        self._items.append(item)
        self._url_repository.add(item)


tFormObject = tObject.register('code_repository_form', base=tBaseObject)

code_repository_list_type = tBaseObject
code_repository_list_handle_type = list_handle_type('code_repository_list', tString)


class CodeRepositoryList(ListObject):

    @classmethod
    def from_data( cls, objinfo, server=None ):
        return cls(code_repository_controller)
    
    def __init__( self, controller ):
        assert isinstance(controller, CodeRepositoryController), repr(controller)
        ListObject.__init__(self)
        self.controller = controller

    def get_title( self ):
        return 'Code repository list'

    def get_commands( self ):
        return [Command('add', 'Add', 'Create code repository url from clipboard', 'Ins')]

    def run_command( self, command_id, initiator_view=None, **kw ):
        if command_id == 'add':
            return self.run_command_add(initiator_view, **kw)
        return ListObject.run_command(self, command_id, initiator_view, **kw)

    def run_command_add( self, initiator_view ):
        return make_code_repository_form()

    def to_data( self ):
        return code_repository_list_type('code_repository_list')

    def get_columns( self ):
        return [Column('name', 'Code Repository name')]

    def get_key_column_id( self ):
        return 'name'

    def fetch_elements( self, sort_column_id, key, desc_count, asc_count ):
        self._notify_fetch_result(self._get_slice())

    def _get_slice( self ):
        items = self.controller.get_items()
        return Slice('name', None, 'asc', map(self._item2element, items), bof=True, eof=True)

    def _item2element( self, item ):
        assert isinstance(item, Item), repr(item)
        return Element(item.name, item, commands=[])


def make_code_repository_list( key=None ):
    object = CodeRepositoryList(code_repository_controller)
    return list_view.Handle(code_repository_list_handle_type, object, sort_column_id='name', key=key)


class GetModulesRequest(Request):

    def __init__( self, iface, path, command_id, params, continuation ):
        Request.__init__(self, iface, path, command_id, params)
        self.continuation = continuation

    def process_response( self, server, response ):
        self.continuation(response.result.modules)


class CodeRepositoryProxy(ProxyObject):

    def __init__( self, server ):
        path = ['code_repository', 'code_repository']
        ProxyObject.__init__(self, server, path, code_repository_iface)

    def get_modules_and_continue( self, module_ids, continuation ):
        command_id = 'get_modules_by_ids'
        params = self.iface.make_params(command_id, module_ids=module_ids)
        request = GetModulesRequest(self.iface, self.path, command_id, params, continuation)
        self.server.execute_request(request)

    def get_required_modules_and_continue( self, requirements, continuation ):
        command_id = 'get_modules_by_requirements'
        params = self.iface.make_params(command_id, requirements=requirements)
        request = GetModulesRequest(self.iface, self.path, command_id, params, continuation)
        self.server.execute_request(request)


code_repository_controller = CodeRepositoryController(
    FileUrlRepository(iface_registry, os.path.expanduser('~/.local/share/hyperapp/client/code_repositories')))
objimpl_registry.register('code_repository_list', CodeRepositoryList.from_data)
