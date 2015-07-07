from .. util import is_list_inst, dt2local_str
from . types import (
    Type,
    TString,
    TInt,
    TBool,
    TOptional,
    Field,
    TRecord,
    TList,
    TIndexedList,
    TRow,
    tCommand,
    )
from . dynamic_record import TDynamicRec, TRegistryRec, Dynamic
from . interface import Command, OpenCommand, tHandle, tObjHandle, Object, Interface


class TListHandle(TDynamicRec):

    def __init__( self ):
        TDynamicRec.__init__(self, base=tObjHandle)

    def resolve_rec( self, rec ):
        assert isinstance(rec.object.iface, ListInterface), repr(rec.object.iface)
        fields = [Field('key', TOptional(TString()))]
        return TRecord(fields=fields, base=self, cls=self.cls)


tListHandle = TListHandle()
ListHandle = tListHandle.instantiate

tHandle.register('list', tListHandle)
tHandle.register('list_narrower', tListHandle)


tColumnType = TRegistryRec()


class ColumnType(Dynamic):

    def to_string( self, value ):
        raise NotImplementedError(self.__class__)


class StrColumnType(ColumnType):

    def __init__( self, discriminator='str' ):
        ColumnType.__init__(self, discriminator)

    def to_string( self, value ):
        return value


class DateTimeColumnType(ColumnType):

    def __init__( self, discriminator='datetime' ):
        ColumnType.__init__(self, discriminator)

    def to_string( self, value ):
        return dt2local_str(value)


tColumnType.register('str', cls=StrColumnType)
tColumnType.register('datetime', cls=DateTimeColumnType)


tColumn = TRecord([
    Field('id', TString()),
    Field('title', TOptional(TString())),
    Field('type', tColumnType),
    ])


class Column(tColumn.make_class()):

    def __init__( self, id, title=None, type=StrColumnType() ):
        super(Column, self).__init__(id, title, type)


class ElementCommand(Command):

    def get_params_fields( self, iface ):
        assert isinstance(iface, ListInterface), repr(iface)  # ElementCommands can only be used with ListInterface
        fields = Command.get_params_fields(self, iface)
        return [Field('element_key', iface.key_type)] + fields


class ElementOpenCommand(ElementCommand, OpenCommand):

    get_params_fields = ElementCommand.get_params_fields
    get_result_type = OpenCommand.get_result_type


class ListObject(Object):

    @classmethod
    def Element( cls, *args, **kw ):
        return cls.iface.Element(*args, **kw)

    @classmethod
    def FetchedElements( cls, *args, **kw ):
        return cls.iface.FetchedElements(*args, **kw)

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


class ListInterface(Interface):
        
    def __init__( self, iface_id, content_fields=None, commands=None, columns=None, key_type=TString() ):
        assert is_list_inst(columns, Type), repr(columns)
        assert isinstance(key_type, Type), repr(key_type)
        self.columns = columns
        self.key_type = key_type
        Interface.__init__(self, iface_id, content_fields, self.tDiff(),
                           (commands or []) + self._get_basic_commands(key_type))

    def get_default_content_fields( self ):
        return Interface.get_default_content_fields(self) + [
            Field('columns', TIndexedList(tColumn)),
            Field('elements', TList(self.tElement())),
            Field('has_more', TBool()),
            Field('selected_key', TOptional(self.key_type)),
            ]

    def _get_basic_commands( self, key_type ):
        return [
            Command('get_elements', [Field('count', TInt()),
                                     Field('key', key_type)],
                                    [Field('fetched_elements', self.tFetchedElements())]),
                ]

    def tFetchedElements( self ):
        return TRecord([
            Field('elements', TList(self.tElement())),
            Field('has_more', TBool()),
            ])

    def FetchedElements( self, *args, **kw ):
        return self.tFetchedElements().instantiate(*args, **kw)

    def tElement( self ):
        return TRecord([
            Field('key', self.key_type),
            Field('row', TRow(self.columns)),
            Field('commands', TList(tCommand)),
            ])

    def Element( self, *args, **kw ):
        return self.tElement().instantiate(*args, **kw)

    def tDiff( self ):
        return TRecord([
            Field('start_key', self.key_type),          # replace elements from this one
            Field('end_key', self.key_type),            # up to (and including) this one
            Field('elements', TList(self.tElement())),  # with these elemenents
            ])

    def Diff( self, *args, **kw ):
        return self.tDiff().instantiate(*args, **kw)
