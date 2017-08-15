import logging
import json
from .method_dispatch import method_dispatch
from .util import encode_path, encode_route
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
    Interface,
    tPath,
    tCommand,
    tServerRoutes,
    tUrl,
    tTypeModule,
    )
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

    def __init__(self, resource_types=None, packet_types=None, iface_registry=None):
        self._resource_types = resource_types
        self._packet_types = packet_types
        self._iface_registry = iface_registry

    def encode(self, t, value):
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
        return RepNode('binary, len=%d' % len(value))

    @dispatch.register(TDateTime)
    def encode_datetime(self, t, value):
        return RepNode(value.isoformat())

    @dispatch.register(TOptional)
    def encode_optional(self, t, value):
        if value is None:
            return RepNode('None')
        return self.dispatch(t.base_t, value)

    @dispatch.register(TList)
    def encode_list(self, t, value):
        if t is tPath:
            return self.encode_path(value)
        if self._packet_types and t is self._packet_types.requirement:
            return RepNode('requirement: %s' % ':'.join(value))
        if self._packet_types and t is self._resource_types.resource_id:
            return RepNode(encode_path(value))
        children = [self.dispatch(t.element_t, elt) for elt in value]
        return RepNode('list (with %d elements)' % len(value), children)

    @dispatch.register(TRecord)
    def encode_record(self, t, value):
        ## print '*** encoding record', value, t, [field.name for field in t.fields]
        if self._packet_types and t is self._packet_types.module:
            return RepNode('module: id=%s, package=%s, satisfies=%r' % (value.id, value.package, value.satisfies))
        if t is tCommand:
            return RepNode('command: command_id=%r, kind=%r, resource_id=%s'
                           % (value.command_id, value.kind, encode_path(value.resource_id)))
        if t is tTypeModule:
            return self._make_type_module_rep(value)
        children = self.encode_record_fields(t.fields, value)
        if t is tServerRoutes:
            public_key = PublicKey.from_der(value.public_key_der)
            return RepNode('server routes: %s -> %r'
                           % (public_key.get_short_id_hex(), [encode_route(route) for route in value.routes]))
        if t is tUrl:
            public_key = PublicKey.from_der(value.public_key_der)
            return RepNode('iface=%s public_key=%s, path=%s'
                           % (value.iface, public_key.get_short_id_hex(), encode_path(value.path)))
        if children:
            return RepNode('record', children)
        else:
            return RepNode('empty record')

    def _make_type_module_rep(self, type_module):
        return RepNode('type module %r' % type_module.module_name, children=[
            RepNode('provided classes: %s' % ', '.join('%s/%s' % (pc.hierarchy_id, pc.class_id) for pc in type_module.provided_classes)),
            RepNode('used_modules: %s' % ', '.join(type_module.used_modules)),
            RepNode('%d typedefs: %s' % (len(type_module.typedefs), ', '.join(typedef.name for typedef in type_module.typedefs))),
            ])

    def encode_record_fields(self, fields, value, custom_encoders=None):
        children = []
        for field in fields:
            custom_encoder = (custom_encoders or {}).get(field.name)
            if custom_encoder:
                rep = custom_encoder(value)
            else:
                rep = self.field_rep(field, value)
            children.append(rep)
        return children

    @dispatch.register(TEmbedded)
    def encode_list(self, t, value):
        return RepNode('<embedded>')

    @dispatch.register(THierarchy)
    def encode_hierarchy_obj(self, t, value):
        tclass = t.resolve_obj(value)
        custom_encoders = {}
        if self._packet_types and self._iface_registry:
            if issubclass(tclass, self._packet_types.client_packet):
                custom_encoders = dict(params=self.encode_client_packet_params)
            if issubclass(tclass, self._packet_types.server_result_response):
                custom_encoders = dict(result=self.encode_server_response_result)
            if issubclass(tclass, self._packet_types.server_error_response):
                custom_encoders = dict(error=self.encode_error_response_error)
        children = self.encode_record_fields(tclass.get_fields(), value, custom_encoders)
        return RepNode('%s %r' % (t.hierarchy_id, tclass.id), children)

    def field_rep(self, field, value):
        rep = self.dispatch(field.type, getattr(value, field.name))
        return RepNode('%s=%s' % (field.name, rep.text), rep.children)

    def encode_path(self, obj):
        return RepNode(encode_path(obj))

    def encode_client_packet_params(self, client_packet):
        iface = self._iface_registry.resolve(client_packet.iface)
        params_t = iface.get_command(client_packet.command_id).params_type
        params = client_packet.params.decode(params_t)
        node = self.dispatch(params_t, params)
        return RepNode('params=' + node.text, node.children)

    def encode_server_response_result(self, server_result_response):
        iface = self._iface_registry.resolve(server_result_response.iface)
        result_t = iface.get_command(server_result_response.command_id).result_type
        result = server_result_response.result.decode(result_t)
        node = self.dispatch(result_t, result)
        return RepNode('result=' + node.text, node.children)

    def encode_error_response_error(self, server_error_response):
        error = server_error_response.error.decode(self._packet_types.error)
        node = self.dispatch(self._packet_types.error, error)
        return RepNode('error=' + node.text, node.children)

def pprint(t, value, resource_types=None, packet_types=None, iface_registry=None):
    rep = VisualRepEncoder(resource_types, packet_types, iface_registry).encode(t, value)
    rep.pprint()
