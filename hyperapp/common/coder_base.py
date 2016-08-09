
class CoderBase(object):

    def __init__( self, iface_registry=None ):
        self._iface_registry = iface_registry

    def get_switched_dynamic_field( self, t, static_fields ):
        assert self._iface_registry, 'IfaceSwitched coding is not supported by this coder: iface_registry is missing'
        return t.get_dynamic_field(self._iface_registry, static_fields)

    def resolve_iface( self, iface_id ):
        assert self._iface_registry, 'IfaceSwitched coding is not supported by this coder: iface_registry is missing'
        return self._iface_registry.resolve(iface_id)
