from method_dispatch import method_dispatch
from . interface import (
    TString,
    TInt,
    TBool,
    TDateTime,
    tString,
    TOptional,
    TRecord,
    TDynamicRec,
    TList,
    TIndexedList,
    TRow,
    THierarchy,
    TObject,
    TIface,
    )


def join_path( *args ):
    return '.'.join(filter(None, args))


class TypeError(Exception): pass


class Mapper(object):

    def map( self, t, value, path='root' ):
        return self.dispatch(t, value, path)

    def expect( self, path, expr, desc ):
        if not expr:
            self.failure(path, desc)

    def failure( self, path, desc ):
        raise TypeError('%s: %s' % (path, desc))

    @method_dispatch
    def dispatch( self, t, value, path ):
        assert False, repr((t, value, path))  # Unknown type

    @dispatch.register(TString)
    @dispatch.register(TInt)
    @dispatch.register(TBool)
    @dispatch.register(TDateTime)
    def map_primitive( self, t, value, path ):
        return value

    @dispatch.register(TOptional)
    def map_optional( self, t, value, path ):
        if value is None:
            return None
        return self.dispatch(t.type, value, path)

    @dispatch.register(TRecord)
    def map_record( self, t, value, path ):
        base_fields = set()
        mapped_fields = {}
        while True:
            new_fields = [field for field in t.get_fields() if field.name not in base_fields]
            mapped_fields.update(self.map_record_fields(new_fields, value, path))
            if t.want_peer_arg:
                mapped_fields.update(peer=value.peer)
            rec = t.instantiate_fixed(**mapped_fields)
            if not isinstance(t, TDynamicRec):
                return rec
            base_fields = set(field.name for field in t.get_fields())
            t = t.resolve_dynamic(rec)

    @dispatch.register(THierarchy)
    def map_hierarchy_obj( self, t, value, path ):
        tclass = t.resolve_obj(value)
        fields = self.map_record_fields(tclass.get_fields(), value, path)
        return tclass.instantiate(**fields)

    def map_record_fields( self, tfields, value, path ):
        fields = {}
        for field in tfields:
            self.expect(path, hasattr(value, field.name), 'Attribute %r is missing' % field.name)
            field_val = getattr(value, field.name)
            elt = self.dispatch(field.type, field_val, join_path(path, field.name))
            fields[field.name] = elt
        return fields

    @dispatch.register(TList)
    def map_list( self, t, value, path ):
        elements = []
        for idx, element_val in enumerate(value):
            mapped_val = self.dispatch(t.element_type, element_val, join_path(path, '#%d' % idx))
            elements.append(mapped_val)
        return elements

    @dispatch.register(TIndexedList)
    def map_indexed_list( self, t, value, path ):
        elements = []
        for idx, element_val in enumerate(value):
            mapped_val = self.dispatch(t.element_type, element_val, join_path(path, '#%d' % idx))
            setattr(mapped_val, 'idx', idx)
            elements.append(mapped_val)
        return elements

    @dispatch.register(TRow)
    def map_row( self, t, value, path ):
        self.expect(path, len(value) == len(t.columns),
                    'Row size mismatch: got %d elements, expected %d' % (len(value), len(t.columns)))
        elements = []
        for idx, (tcol, element_val) in enumerate(zip(t.columns, value)):
            mapped_val = self.dispatch(tcol, element_val, join_path(path, '#%d' % idx))
            elements.append(mapped_val)
        return elements

    @dispatch.register(TIface)
    def map_iface( self, t, value, path ):
        return value
