import abc
import base64
import json
import yaml
import dateutil.parser
from .method_dispatch import method_dispatch
from .htypes import (
    TString,
    TBinary,
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
from .coder_base import CoderBase


def join_path( *args ):
    return '.'.join([_f for _f in args if _f])


class DecodeError(Exception): pass


class DictDecoder(CoderBase, metaclass=abc.ABCMeta):

    def decode( self, t, value, path='root' ):
        assert isinstance(value, bytes), repr(value)
        return self.dispatch(t, self._str_to_dict(value.decode()), path)

    @abc.abstractmethod
    def _str_to_dict( self, value ):
        pass

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
        self.expect_type(path, isinstance(value, str), value, 'string')
        return value

    @dispatch.register(TBinary)
    def decode_primitive( self, t, value, path ):
        self.expect_type(path, isinstance(value, str), value, 'string')
        return base64.b64decode(value)

    @dispatch.register(TInt)
    def decode_primitive( self, t, value, path ):
        self.expect_type(path, isinstance(value, int), value, 'integer')
        return value

    @dispatch.register(TBool)
    def decode_primitive( self, t, value, path ):
        self.expect_type(path, isinstance(value, bool), value, 'bool')
        return value

    @dispatch.register(TDateTime)
    def decode_datetime( self, t, value, path ):
        self.expect_type(path, isinstance(value, str), value, 'datetime (string)')
        return dateutil.parser.parse(value)

    @dispatch.register(TOptional)
    def decode_optional( self, t, value, path ):
        if value is None:
            return None
        return self.dispatch(t.base_t, value, path)

    @dispatch.register(TRecord)
    def decode_record( self, t, value, path ):
        self.expect_type(path, isinstance(value, dict), value, 'record (dict)')
        fields = self.decode_record_fields(t, value, path)
        return t(**fields)

    @dispatch.register(THierarchy)
    def decode_hierarchy_obj( self, t, value, path ):
        self.expect_type(path, isinstance(value, dict), value, 'hierarchy object (dict)')
        self.expect(path, '_class_id' in value, '_class_id field is missing')
        id = self.dispatch(tString, value['_class_id'], join_path(path, '_class_id'))
        tclass = t.resolve(id)
        fields = self.decode_record_fields(tclass.get_trecord(), value, path)
        return tclass(**fields)

    def decode_record_fields( self, t, value, path ):
        fields = {}
        for field in t.get_static_fields():
            fields[field.name] = self.decode_record_field(field, value, path)
        if isinstance(t, TSwitchedRec):
            dyn_field = self.get_switched_dynamic_field(t, fields)
            fields[dyn_field.name] = self.decode_record_field(dyn_field, value, path)
            # TIfaceSwitched expectes Interface instance as first argument, not iface id
            fields['iface'] = self.resolve_iface(fields['iface'])
        return fields

    def decode_record_field( self, field, value, path ):
        self.expect(path, field.name in value, 'field %r is missing' % field.name)
        return self.dispatch(field.type, value[field.name], join_path(path, field.name))

    @dispatch.register(TList)
    def decode_list( self, t, value, path ):
        self.expect_type(path, isinstance(value, list), value, 'list')
        return [self.dispatch(t.element_t, elt, join_path(path, '#%d' % idx))
                for idx, elt in enumerate(value)]

    @dispatch.register(TIndexedList)
    def decode_list( self, t, value, path ):
        self.expect_type(path, isinstance(value, list), value, 'list')
        decoded_elts = []
        for idx, elt in enumerate(value):
            decoded_elt = self.dispatch(t.element_t, elt, join_path(path, '#%d' % idx))
            setattr(decoded_elt, 'idx', idx)
            decoded_elts.append(decoded_elt)
        return decoded_elts


class JsonDecoder(DictDecoder):

    def _str_to_dict( self, value ):
        return json.loads(value)


class YamlDecoder(DictDecoder):

    def _str_to_dict( self, value ):
        return yaml.load(value)
