import json
import dateutil.parser
from .method_dispatch import method_dispatch
from .htypes import (
    TString,
    TInt,
    TBool,
    TDateTime,
    tString,
    TOptional,
    TRecord,
    TList,
    TIndexedList,
    TSwitchedRec,
    THierarchy,
    )


def join_path( *args ):
    return '.'.join(filter(None, args))


class DecodeError(Exception): pass


class JsonDecoder(object):

    def decode( self, t, value, path='root' ):
        return self.dispatch(t, json.loads(value), path)

    def expect( self, path, expr, desc ):
        if not expr:
            self.failure(path, desc)

    def expect_type( self, path, expr, value, type_name ):
        if not expr:
            self.failure(path, '%s is expected, but got: %r' % (type_name, value))

    def failure( self, path, desc ):
        raise DecodeError('%s: %s' % (path, desc))

    @method_dispatch
    def dispatch( self, t, value, path ):
        assert False, repr((t, path, value))  # Unknown type

    @dispatch.register(TString)
    def decode_primitive( self, t, value, path ):
        self.expect_type(path, isinstance(value, basestring), value, 'string')
        return value

    @dispatch.register(TInt)
    def decode_primitive( self, t, value, path ):
        self.expect_type(path, isinstance(value, (int, long)), value, 'integer')
        return value

    @dispatch.register(TBool)
    def decode_primitive( self, t, value, path ):
        self.expect_type(path, isinstance(value, bool), value, 'bool')
        return value

    @dispatch.register(TDateTime)
    def decode_datetime( self, t, value, path ):
        self.expect_type(path, isinstance(value, basestring), value, 'datetime (string)')
        return dateutil.parser.parse(value)

    @dispatch.register(TOptional)
    def decode_optional( self, t, value, path ):
        if value is None:
            return None
        return self.dispatch(t.type, value, path)

    @dispatch.register(TRecord)
    def decode_record( self, t, value, path ):
        self.expect_type(path, isinstance(value, dict), value, 'record (dict)')
        fields = self.decode_record_fields(t, value, path)
        return t.instantiate(**fields)

    @dispatch.register(THierarchy)
    def decode_hierarchy_obj( self, t, value, path ):
        self.expect_type(path, isinstance(value, dict), value, 'hierarchy object (dict)')
        self.expect(path, '_class_id' in value, '_class_id field is missing')
        id = self.dispatch(tString, value['_class_id'], join_path(path, '_class_id'))
        tclass = t.resolve(id)
        fields = self.decode_record_fields(tclass.get_trecord(), value, path)
        return tclass.instantiate(**fields)

    def decode_record_fields( self, t, value, path ):
        fields = self.decode_record_fields_impl(t.get_static_fields(), value, path)
        if isinstance(t, TSwitchedRec):
            fields.update(self.decode_record_fields_impl([t.get_dynamic_field(fields)], value, path))
        return fields

    def decode_record_fields_impl( self, tfields, value, path ):
        fields = {}
        for field in tfields:
            self.expect(path, field.name in value, 'field %r is missing' % field.name)
            elt = self.dispatch(field.type, value[field.name], join_path(path, field.name))
            fields[field.name] = elt
        return fields

    @dispatch.register(TList)
    def decode_list( self, t, value, path ):
        self.expect_type(path, isinstance(value, list), value, 'list')
        return [self.dispatch(t.element_type, elt, join_path(path, '#%d' % idx))
                for idx, elt in enumerate(value)]

    @dispatch.register(TIndexedList)
    def decode_list( self, t, value, path ):
        self.expect_type(path, isinstance(value, list), value, 'list')
        decoded_elts = []
        for idx, elt in enumerate(value):
            decoded_elt = self.dispatch(t.element_type, elt, join_path(path, '#%d' % idx))
            setattr(decoded_elt, 'idx', idx)
            decoded_elts.append(decoded_elt)
        return decoded_elts
