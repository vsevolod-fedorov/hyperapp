from PySide import QtCore, QtGui
from command import ObjectCommand, ElementCommand
import iface_registry


class Column(object):

    def __init__( self, idx, id, title ):
        self.idx = idx
        self.id = id
        self.title = title

    @classmethod
    def from_json( cls, idx, data ):
        return cls(idx, data['id'], data['title'])


class Element(object):

    def __init__( self, row, commands ):
        self.row = row
        self.commands = commands

    @classmethod
    def from_json( cls, data ):
        return cls(data['row'], [ElementCommand.from_json(cmd) for cmd in data['commands']])


class ListObj(object):

    def __init__( self, server, response ):
        self.server = server
        self.path = response['path']
        self.obj_commands = [ObjectCommand.from_json(cmd) for cmd in response['commands']]
        self.columns = [Column.from_json(idx, column) for idx, column in enumerate(response['columns'])]
        self.elements = [Element.from_json(elt) for elt in response['elements']]
        self.key_column_idx = self._find_key_column(self.columns)

    def title( self ):
        return self.path

    def element_count( self ):
        return len(self.elements)

    def ensure_element_count( self, element_count ):
        if element_count < self.element_count(): return
        self.load_elements(element_count - self.element_count())

    def element_idx2key( self, idx ):
        return self.elements[idx].row[self.key_column_idx]

    def element2key( self, elt ):
        return elt.row[self.key_column_idx]

    def load_elements( self, load_count ):
        if self.elements:
            last_key = self.element_idx2key(-1)
        else:
            last_key = None
        request = dict(
            method='get_elements',
            path=self.path,
            key=last_key,
            count=load_count)
        response = self.server.execute_request(request)
        self.elements += [Element.from_json(elt) for elt in response['elements']]

    def get_obj_commands( self ):
        return self.obj_commands

    def _find_key_column( self, columns ):
        for idx, col in enumerate(columns):
            if col.id == 'key':
                return col.idx
        assert False, 'No "key" column'


iface_registry.register_iface('list', ListObj)
