from functools import total_ordering
from .util import is_list_inst
from .htypes import ListInterface
from .diff import Diff
from .command import Command


@total_ordering
class Element(object):

    @classmethod
    def from_data(cls, iface, rec):
        key = getattr(rec.row, iface.get_key_column_id())
        return cls(key, rec.row, [Command(id) for id in rec.commands])

    def __init__(self, key, row, commands=None, order_key=None):
        assert is_list_inst(commands or [], Command), repr(commands)
        self.key = key
        self.row = row
        self.commands = commands or []
        if order_key is not None:
            self.order_key = order_key

    def __repr__(self):
        return '<Element #%r %r>' % (self.key, self.row)

    def to_data(self, iface):
        assert isinstance(iface, ListInterface), repr(iface)
        return iface.Element(self.row, [cmd.id for cmd in self.commands])

    def __eq__(self, other):
        if isinstance(other, Element):
            return self.order_key == other.order_key
        else:
            return self.order_key == other

    def __lt__(self, other):
        if isinstance(other, Element):
            return self.order_key < other.order_key
        else:
            return self.order_key < other

    def clone_with_sort_column(self, sort_column_id):
        order_key = getattr(self.row, sort_column_id)
        return Element(self.key, self.row, self.commands, order_key)


class Slice(object):

    def __init__(self, sort_column_id, from_key, elements, bof, eof):
        assert isinstance(sort_column_id, str), repr(sort_column_id)
        assert is_list_inst(elements, Element), repr(elements)
        self.sort_column_id = sort_column_id
        self.from_key = from_key
        self.elements = elements
        self.bof = bof
        self.eof = eof

    def __eq__(self, other):
        if not isinstance(other, Slice):
            return False
        return (self.sort_column_id == other.sort_column_id
                and self.from_key == other.from_key
                and self.elements == other.elements
                and self.bof == other.bof
                and self.eof == other.eof)

    def __repr__(self):
        return ('Slice(sort_column_id=%r from_key=%r bof=%r eof=%r %d elements %s)'
                % (self.sort_column_id, self.from_key, self.bof, self.eof, len(self.elements),
                   'from %r to %r' % (self.elements[0].key, self.elements[-1].key) if self.elements else ''))

    def to_data(self, iface):
        assert isinstance(iface, ListInterface), repr(iface)
        elements = [elt.to_data(iface) for elt in self.elements]
        return iface.Slice(self.sort_column_id, self.from_key, elements, self.bof, self.eof)

    def clone_with_elements(self, elements):
        return Slice(self.sort_column_id, self.from_key, elements, self.bof, self.eof)


class ListDiff(Diff):

    @classmethod
    def add_one(cls, key, element):
        return cls(key, key, [element])

    @classmethod
    def add_many(cls, key, elements):
        return cls(key, key, elements)

    @classmethod
    def append_many(cls, elements):
        return cls.add_many(None, elements)

    @classmethod
    def replace(cls, key, element):
        return cls(key, key, [element])

    @classmethod
    def delete(cls, key):
        return cls(key, key, [])

    @classmethod
    def from_data(cls, iface, rec):
        return cls(rec.start_key, rec.end_key, [Element.from_data(iface, element) for element in rec.elements])

    def __init__(self, start_key, end_key, elements):
        assert is_list_inst(elements, Element), repr(elements)
        # keys == None means append
        self.start_key = start_key  # replace elements from this one
        self.end_key = end_key      # up to (and including) this one
        self.elements = elements    # with these elemenents

    def __repr__(self):
        return 'ListDiff(%r-%r>%r)' % (self.start_key, self.end_key, self.elements)

    def to_data(self, iface):
        assert isinstance(iface, ListInterface), repr(iface)
        return iface.Diff(self.start_key, self.end_key, [element.to_data(iface) for element in self.elements])