import os.path
import uuid
from PySide import QtCore, QtGui
from ..common.htypes import (
    tString,
    tBaseObject,
    IfaceRegistry,
    iface_registry,
    Column,
    list_handle_type,
    )
from ..common.endpoint import Url
from .module import Module
from .objimpl_registry import objimpl_registry
from .command import Command, ElementCommand
from .list_object import Element, Slice, ListObject
from .proxy_object import GetRequest
from . import list_view
from .named_url_file_repository import NamedUrl, UrlFileRepository


class Bookmarks(object):

    def __init__( self, repository ):
        assert isinstance(repository, UrlFileRepository), repr(repository)
        self._repository = repository
        self._items = list(self._repository.enumerate())  # NamedUrl list
        self._id2item = dict((item.id, item) for item in self._items)

    def get_items( self ):
        return self._items

    def get_item( self, id ):
        return self._id2item[id]

    def add( self, name, url ):
        id = str(uuid.uuid4())
        item = NamedUrl(id, name, url)
        self._items.append(item)
        self._id2item[item.id] = item
        self._repository.add(item)
        return item


bookmark_list_type = tBaseObject
bookmark_list_handle_type = list_handle_type('bookmark_list', tString)


class BookmarkList(ListObject):

    @classmethod
    def from_data( cls, objinfo, server=None ):
        return cls(iface_registry, this_module.bookmarks)
    
    def __init__( self, iface_registry, bookmarks ):
        assert isinstance(iface_registry, IfaceRegistry), repr(iface_registry)
        assert isinstance(bookmarks, Bookmarks), repr(bookmarks)
        ListObject.__init__(self)
        self._iface_registry = iface_registry
        self._bookmarks = bookmarks

    def get_title( self ):
        return 'Bookmarks'

    def get_commands( self ):
        return [Command('add', 'Add', 'Add url from clipboard', 'Ins')]

    def run_command( self, command_id, initiator_view=None, **kw ):
        if command_id == 'open':
            return self.run_command_open(initiator_view, **kw)
        if command_id == 'add':
            return self.run_command_add(initiator_view, **kw)
        return ListObject.run_command(self, command_id, initiator_view, **kw)

    def run_command_open( self, initiator_view, element_key ):
        item = self._bookmarks.get_item(element_key)
        GetRequest(item.url, initiator_view).execute()

    def run_command_add( self, initiator_view ):
        url_str = QtGui.QApplication.clipboard().text()
        url = Url.from_str(self._iface_registry, url_str)
        name = 'Imported url'
        item = self._bookmarks.add(name, url)
        return make_bookmark_list(item.name)

    def to_data( self ):
        return bookmark_list_type('bookmark_list')

    def get_columns( self ):
        return [
            Column('id'),
            Column('name', 'Bookmark name'),
            ]

    def get_key_column_id( self ):
        return 'id'

    def fetch_elements( self, sort_column_id, key, desc_count, asc_count ):
        self._notify_fetch_result(self._get_slice())

    def _get_slice( self ):
        items = self._bookmarks.get_items()
        return Slice('id', None, 'asc', map(self._item2element, items), bof=True, eof=True)

    def _item2element( self, item ):
        assert isinstance(item, NamedUrl), repr(item)
        commands = [ElementCommand('open', 'Open', 'Open selected bookmark')]
        return Element(item.id, item, commands=commands)


def make_bookmark_list( key=None ):
    object = BookmarkList(iface_registry, this_module.bookmarks)
    return list_view.Handle(bookmark_list_handle_type, object, sort_column_id='name', key=key)


class ThisModule(Module):

    def __init__( self ):
        Module.__init__(self)
        self.bookmarks = Bookmarks(UrlFileRepository(
            iface_registry, os.path.expanduser('~/.local/share/hyperapp/client/bookmarks')))
        objimpl_registry.register('bookmark_list', BookmarkList.from_data)


this_module = ThisModule()
