import abc
import base64
import codecs
import json
import yaml
from .method_dispatch import method_dispatch
from .htypes import (
    TNone,
    TString,
    TBinary,
    TInt,
    TBool,
    TDateTime,
    tString,
    TOptional,
    TRecord,
    TException,
    TList,
    Interface,
    ref_t,
    )
from .htypes.deduce_value_type import deduce_value_type


class DictEncoder(metaclass=abc.ABCMeta):

    def __init__(self, mosaic=None):
        self._mosaic = mosaic

    def encode(self, value, t=None):
        t = t or deduce_value_type(value)
        return self._encode_dict(self.dispatch(t, value))

    def _encode_dict(self, value):
        return value

    @method_dispatch
    def dispatch(self, t, value):
        assert False, repr((t, value))  # Unknown type

    @dispatch.register(TNone)
    def encode_primitive(self, t, value):
        return None

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
    @dispatch.register(TException)
    def encode_record(self, t, value):
        if t is ref_t and self._mosaic:
            # Mosaic is defined for yaml encoder - to embed ref value.
            return self._encode_ref(value)
        fields = {}
        for field_name, field_type in t.fields.items():
            attr = getattr(value, field_name)
            fields[field_name] = self.dispatch(field_type, attr)
        return fields

    @dispatch.register(TList)
    def _encode_list(self, t, value):
        return self.encode_list(t, value)

    def encode_list(self, t, value):
        return [self.dispatch(t.element_t, elt) for elt in value]

    def _encode_ref(self, ref):
        decoded_capsule = self._mosaic.resolve_ref(ref)
        value = self.dispatch(decoded_capsule.t, decoded_capsule.value)
        type_ref = decoded_capsule.type_ref
        hash_str = codecs.encode(type_ref.hash, "hex").decode('ascii')
        type_ref_str = f'{type_ref.hash_algorithm}:{hash_str}'
        return dict(
            type_ref=type_ref_str,
            type_name=decoded_capsule.t.name,  # Ignored by decoder - just for readability.
            value=value,
            )


class JsonEncoder(DictEncoder):

    def __init__(self, pretty=True):
        super().__init__()
        self._pretty = pretty

    def _encode_dict(self, value):
        return json.dumps(value, indent=2 if self._pretty else None).encode()


class YamlEncoder(DictEncoder):

    def _encode_dict(self, value):
        return yaml.dump(value).encode()
