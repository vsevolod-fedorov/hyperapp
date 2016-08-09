# record with some field is of variable type, switched by other field values

from ..util import is_list_inst, is_tuple_inst
from .htypes import join_path, Type, Field, TRecord
from .interface import Interface


class TSwitched(Type):

    def __instancecheck__( self, value ):
        return True


tSwitched = TSwitched()


class TIfaceSwitchedRec(TRecord):

    def __init__( self, fields=None, base=None ):
        #assert isinstance(base, TSwitchedRec)  # either switches must be defined, or base must be a TSwitchedRec
        TRecord.__init__(self, fields, base)
        self._dynamic_field = self._pick_dynamic_field()

    def get_static_fields( self ):
        return [field for field in self.get_fields() if field is not self._dynamic_field]

    # get Field with actual dynamic type
    def get_dynamic_field( self, iface_registry, static_fields_dict ):
        iface_id, = self._pick_switch(['iface'], static_fields_dict)
        iface = iface_registry.resolve(iface_id)
        t = iface.get_diff_type()
        return Field(self._dynamic_field.name, t)

    def _pick_dynamic_field( self ):
        dynamic_field = None
        for field in self.fields:
            if field.type is tSwitched:
                assert dynamic_field is None, repr((dynamic_field.name, field.name))  # only one dynamic field is supported
                dynamic_field = field
        assert dynamic_field is not None  # one field with type=tSwitched is expected
        return dynamic_field

    def _pick_switch( self, switches, fields_dict ):
        return tuple(fields_dict[name] for name in switches)

    def adopt_args( self, iface, *args, **kw ):
        assert isinstance(iface, Interface), repr(iface)
        adopted_args = TRecord.adopt_args(self, iface.iface_id, *args, **kw)
        dyn_name = self._dynamic_field.name
        dyn_type = iface.get_diff_type()
        assert isinstance(adopted_args[dyn_name], dyn_type), \
          'Field %r is expected to be %r, but is %r' % (dyn_name, dyn_type, adopted_args[dyn_name])
        return adopted_args


class TUpdatesRec(TIfaceSwitchedRec):
    pass


TSwitchedRec = TUpdatesRec  # temporary import hack
