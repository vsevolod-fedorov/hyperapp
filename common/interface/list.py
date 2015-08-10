from .. util import is_list_inst, dt2local_str
from . types import (
    Type,
    tString,
    tInt,
    tBool,
    tDateTime,
    TOptional,
    Field,
    TRecord,
    TList,
    TIndexedList,
    tCommand,
    )
from . hierarchy import THierarchy
from . interface import RequestCmd, OpenCommand, tHandle, tObjHandle, Object, Interface


class ColumnType(object):

    def to_string( self, value ):
        raise NotImplementedError(self.__class__)


class StringColumnType(ColumnType):

    type = tString

    def to_string( self, value ):
        return value


class IntColumnType(ColumnType):

    type = tInt

    def to_string( self, value ):
        return str(value)


class DateTimeColumnType(ColumnType):

    type = tDateTime

    def to_string( self, value ):
        return dt2local_str(value)


stringColumnType = StringColumnType()
intColumnType = IntColumnType()
dateTimeColumnType = DateTimeColumnType()


class Column(object):

    def __init__( self, id, title=None, type=StringColumnType() ):
        assert isinstance(id, basestring), repr(id)
        assert title is None or isinstance(title, basestring), repr(title)
        assert isinstance(type, ColumnType), repr(type)
        self.id = id
        self.title = title
        self.type = type


class ElementCommand(RequestCmd):

    def get_params_fields( self, iface ):
        assert isinstance(iface, ListInterface), repr(iface)  # ElementCommands can only be used with ListInterface
        fields = RequestCmd.get_params_fields(self, iface)
        return [Field('element_key', iface.key_type)] + fields


class ElementOpenCommand(ElementCommand, OpenCommand):

    get_params_fields = ElementCommand.get_params_fields
    get_result_type = OpenCommand.get_result_type


class ListObject(Object):

    @classmethod
    def Row( cls, *args, **kw ):
        return cls.iface.Row(*args, **kw)

    @classmethod
    def Element( cls, *args, **kw ):
        return cls.iface.Element(*args, **kw)

    @classmethod
    def Diff( cls, *args, **kw ):
        return cls.iface.Diff(*args, **kw)

    @classmethod
    def Diff_insert_one( cls, key, element ):
        return cls.Diff_insert_many(key, [element])

    @classmethod
    def Diff_insert_many( cls, key, elements ):
        return cls.Diff(key, key, elements)

    @classmethod
    def Diff_append_many( cls, elements ):
        return cls.Diff.insert_many(None, elements)

    @classmethod
    def Diff_delete( cls, key ):
        return cls.Diff(key, key, [])

    @classmethod
    def ListHandle( cls, *args, **kw ):
        return cls.iface.ListHandle('list', *args, **kw)

    @classmethod
    def ListNarrowerHandle( cls, *args, **kw ):
        return cls.iface.ListNarrowerHandle('list_narrower', *args, **kw)


class ListInterface(Interface):
        
    def __init__( self, iface_id, base=None, content_fields=None, commands=None, columns=None, key_column='key' ):
        assert is_list_inst(columns, Column), repr(columns)
        assert isinstance(key_column, basestring), repr(key_column)
        self.columns = columns
        self.key_column = key_column
        self.key_type = self._pick_key_column().type.type  # used by parent __init__
        self.tRowRecord = TRecord([Field(column.id, column.type.type) for column in columns])  # --//--
        Interface.__init__(self, iface_id, base, content_fields, self.tDiff(), commands)
        self._register_types()

    def _pick_key_column( self ):
        for column in self.columns:
            if column.id == self.key_column:
                return column
        assert False, repr((self.key_column, [column.id for column in self.columns]))  # unknown key column

    def _register_types( self ):
        list_fields = [Field('key', TOptional(self.key_type))]
        narrower_fields = [Field('field_id', tString),
                           Field('key', TOptional(self.key_type))]
        self._tListHandle = tHandle.register(
            '%s.list' % self.iface_id, list_fields, base=tObjHandle)
        self._tListNarrowerHandle = tHandle.register(
            '%s.list_narrower' % self.iface_id, narrower_fields, base=tObjHandle)

    def get_default_content_fields( self ):
        return Interface.get_default_content_fields(self) + [
            Field('sorted_by_column', tString),
            Field('elements', TList(self.tElement())),
            Field('bof', tBool),
            Field('eof', tBool),
            ]

    def get_basic_commands( self ):
        fetch_params_fields = [
            Field('sort_by_column', tString),
            Field('key', TOptional(self.key_type)),
            Field('desc_count', tInt),
            Field('asc_count', tInt),
            ]
        fetch_result_fields = [
            Field('elements', TList(self.tElement())),
            Field('bof', tBool),
            Field('eof', tBool),
            ]
        return Interface.get_basic_commands(self) \
            + [RequestCmd('fetch_elements', fetch_params_fields, fetch_result_fields),
               RequestCmd('subscribe_and_fetch_elements', fetch_params_fields, fetch_result_fields)]

    def Row( self, *args, **kw ):
        return self.tRowRecord.instantiate(*args, **kw)

    def tElement( self ):
        return TRecord([
            Field('row', self.tRowRecord),
            Field('commands', TList(tCommand)),
            ])

    def Element( self, row, commands=None ):
        return self.tElement().instantiate(row, commands or [])

    def tDiff( self ):
        return TRecord([
            Field('start_key', self.key_type),          # replace elements from this one
            Field('end_key', self.key_type),            # up to (and including) this one
            Field('elements', TList(self.tElement())),  # with these elemenents
            ])

    def Diff( self, *args, **kw ):
        return self.tDiff().instantiate(*args, **kw)

    def ListHandle( self, *args, **kw ):
        return self._tListHandle.instantiate(*args, **kw)

    def ListNarrowerHandle( self, *args, **kw ):
        return self._tListNarrowerHandle.instantiate(*args, **kw)
