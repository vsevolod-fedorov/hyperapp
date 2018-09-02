import logging
import json
import codecs

from .interface import hyper_ref as href_types
from .interface import module as module_types
from .interface import resource as resource_types
from .method_dispatch import method_dispatch
from .util import encode_path, encode_route, full_type_name_to_str
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
    TEmbedded,
    THierarchy,
    TClass,
    Interface,
    tPath,
    tCommand,
    tServerRoutes,
    tTypeModule,
    )
from .htypes.deduce_value_type import deduce_value_type
from .ref import ref_repr, make_ref
from .identity import PublicKey

log = logging.getLogger(__name__)


class RepNode(object):

    def __init__(self, text, children=None):
        self.text = text
        self.children = children or []

    def pprint(self, indent=0):
        log.info('%s%s' % ('  ' * indent, self.text))
        for node in self.children:
            node.pprint(indent + 1)


class VisualRepEncoder(object):

    def __init__(self):
        pass

    def encode(self, value, t):
        assert isinstance(value, t), repr(value)
        return self.dispatch(t, value)

    @method_dispatch
    def dispatch(self, t, value):
        assert False, repr((t, value))  # Unknown type

    @dispatch.register(TString)
    @dispatch.register(TInt)
    @dispatch.register(TBool)
    def encode_primitive(self, t, value):
        return RepNode(repr(value))

    @dispatch.register(TBinary)
    def encode_binary(self, t, value):
        if t is href_types.ref:
            return RepNode('%s' % ref_repr(value))
        return RepNode('binary, len=%d: %s' % (len(value), codecs.encode(value[:40], 'hex')))

    @dispatch.register(TDateTime)
    def encode_datetime(self, t, value):
        return RepNode(value.isoformat())

    @dispatch.register(TOptional)
    def encode_optional(self, t, value):
        if value is None:
            return RepNode('None')
        return self.dispatch(t.base_t, value)

    @staticmethod
    def _make_name(t, type_name):
        if t.full_name:
            return '%s (%s)' % ('.'.join(t.full_name), type_name)
        else:
            return type_name

    @dispatch.register(TList)
    def encode_list(self, t, value):
        if t is href_types.full_type_name:
            return RepNode('%r' % full_type_name_to_str(value))
        if t is tPath:
            return self.encode_path(value)
        if t is module_types.requirement:
            return RepNode('requirement: %s' % ':'.join(value))
        if t is resource_types.resource_id:
            return RepNode(encode_path(value))
        children = [self.dispatch(t.element_t, elt) for elt in value]
        return RepNode('%s (%d elements)' % (self._make_name(t, 'list'), len(value)), children)

    @dispatch.register(TRecord)
    def encode_record(self, t, value):
        ## print '*** encoding record', value, t, [field.name for field in t.fields]
        if t is href_types.capsule:
            ref = make_ref(value)
            return RepNode('capsule %s: %s (%s)' % (ref_repr(ref), full_type_name_to_str(value.full_type_name), value.encoding))
        if t is href_types.route:
            return RepNode('route: %s -> %s' % (ref_repr(value.endpoint_ref), ref_repr(value.transport_ref)))
        if t is module_types.module:
            return RepNode('module: id=%s, package=%s, satisfies=%r' % (value.id, value.package, value.satisfies))
        if t is tCommand:
            return RepNode('command: command_id=%r, kind=%r, resource_id=%s'
                           % (value.command_id, value.kind, encode_path(value.resource_id)))
#        if t is tTypeModule:
#            return self._make_type_module_rep(value)
        custom_encoders = None
#        if self._iface_registry and issubclass(t, packet_types.update):
#            custom_encoders = dict(diff=self.encode_update_diff)
        children = self.encode_record_fields(t.fields, value, custom_encoders)
        if t is tServerRoutes:
            public_key = PublicKey.from_der(value.public_key_der)
            return RepNode('server routes: %s -> %r'
                           % (public_key.get_short_id_hex(), [encode_route(route) for route in value.routes]))
        if children:
            return RepNode(self._make_name(t, 'record'), children)
        else:
            return RepNode('%s: empty' % self._make_name(t, 'record'))

#    def _make_type_module_rep(self, type_module):
#        return RepNode('type module %r' % type_module.module_name, children=[
#            RepNode('provided classes: %s' % ', '.join('%s/%s' % (pc.hierarchy_id, pc.class_id) for pc in type_module.provided_classes)),
#            RepNode('used_modules: %s' % ', '.join(type_module.used_modules)),
#            RepNode('%d typedefs: %s' % (len(type_module.typedefs), ', '.join(typedef.name for typedef in type_module.typedefs))),
#            ])

    def encode_record_fields(self, fields, value, custom_encoders=None):
        children = []
        for field in fields:
            custom_encoder = (custom_encoders or {}).get(field.name)
            rep = self.field_rep(field, value, custom_encoder)
            children.append(rep)
        return children

    def field_rep(self, field, value, custom_encoder):
        if custom_encoder:
            rep = custom_encoder(value)
        else:
            rep = self.dispatch(field.type, getattr(value, field.name))
        return RepNode('%s=%s' % (field.name, rep.text), rep.children)

    @dispatch.register(TEmbedded)
    def encode_list(self, t, value):
        return RepNode('<%s>' % self._make_name(t, 'embedded'))

    @dispatch.register(THierarchy)
    def encode_hierarchy_obj(self, t, value):
        tclass = t.get_object_class(value)
        custom_encoders = {}
        children = self.encode_record_fields(tclass.get_fields(), value, custom_encoders)
        return RepNode('%s %r %r' % (self._make_name(t, 'hierarchy'), t.hierarchy_id, tclass.id), children)

    @dispatch.register(TClass)
    def encode_tclass_obj(self, t, value):
        assert isinstance(value, t), repr((t, value))
        return self.encode_hierarchy_obj(t.hierarchy, value)

    def encode_path(self, obj):
        return RepNode(encode_path(obj))


def pprint(value, t=None, indent=0, title=None):
    t = t or deduce_value_type(value)
    rep = VisualRepEncoder().encode(value, t)
    if title:
        log.info(title)
        indent += 1
    rep.pprint(indent)