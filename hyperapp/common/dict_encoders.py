import abc
import base64
import json
import yaml
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
    EncodableEmbedded,
    TEmbedded,
    THierarchy,
    TClass,
    Interface,
    ref_t,
    )
from .htypes.deduce_value_type import deduce_value_type


class DictEncoder(metaclass=abc.ABCMeta):

    def __init__(self, type_resolver=None):
        self._type_resolver = type_resolver

    def encode(self, value, t=None):
        t = t or deduce_value_type(value)
        return self._encode_dict(self.dispatch(t, value))

    def _encode_dict(self, value):
        return value

    @method_dispatch
    def dispatch(self, t, value):
        assert False, repr((t, value))  # Unknown type

    @dispatch.register(TString)
    @dispatch.register(TInt)
    @dispatch.register(TBool)
    def encode_primitive(self, t, value):
        return value

    @dispatch.register(TBinary)
    def encode_binary(self, t, value):
        return str(base64.b64encode(value), 'ascii')

    @dispatch.register(TDateTime)
    def encode_datetime(self, t, value):
        return value.isoformat()

    @dispatch.register(TOptional)
    def encode_optional(self, t, value):
        if value is None:
            return None
        return self.dispatch(t.base_t, value)

    @dispatch.register(TRecord)
    def encode_record(self, t, value):
        if t is ref_t and self._type_resolver:
            return self._encode_ref(value)
        fields = {}
        for field_name, field_type in t.fields.items():
            attr = getattr(value, field_name)
            fields[field_name] = self.dispatch(field_type, attr)
        return fields

    @dispatch.register(TList)
    def encode_list(self, t, value):
        return [self.dispatch(t.element_t, elt) for elt in value]

    @dispatch.register(TEmbedded)
    def encode_embedded(self, t, value):
        assert isinstance(value, EncodableEmbedded), repr(value)
        return self.dispatch(value.type, value.value)

    @dispatch.register(THierarchy)
    def encode_hierarchy_obj(self, t, value):
        tclass = t.get_object_class(value)
        return dict(self.encode_record(tclass, value),
                    _class_id=self.dispatch(tString, tclass.id))

    @dispatch.register(TClass)
    def encode_tclass_obj(self, t, value):
        assert isinstance(value, t), repr((t, value))
        return self.encode_hierarchy_obj(t.hierarchy, value)

    def _encode_ref(self, ref):
        decoded_capsule = self._type_resolver.resolve_ref(ref)
        return self.dispatch(decoded_capsule.t, decoded_capsule.value)


class JsonEncoder(DictEncoder):

    def __init__(self, pretty=True):
        super().__init__()
        self._pretty = pretty

    def _encode_dict(self, value):
        return json.dumps(value, indent=2 if self._pretty else None).encode()


class YamlEncoder(DictEncoder):

    def _encode_dict(self, value):
        return yaml.dump(value).encode()
