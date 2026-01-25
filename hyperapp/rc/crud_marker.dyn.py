import logging

from hyperapp.boot.htypes import TRecord

from . import htypes
from .services import (
    deduce_t,
    pyobj_creg,
    )
from .code.marker_utils import (
    check_is_function,
    check_not_classmethod,
    split_actor_params,
    )
from .code.crud_ctr import CrudInitTemplateCtr, CrudCommitTemplateCtr

log = logging.getLogger(__name__)


class CrudProbe:

    def __init__(self, system_probe, ctr_collector, module_name, action_name, fn):
        self._system = system_probe
        self._ctr_collector = ctr_collector
        self._module_name = module_name
        self._action_name = action_name
        self._fn = fn
        system_probe.add_global(self)

    def migrate_to(self, system_probe):
        self._system = system_probe
        self._ctr_collector = system_probe.resolve_service('ctr_collector')

    def __call__(self, *args, **kw):
        params = split_actor_params(self._fn, args, kw)
        service_kw = {
            name: self._system.resolve_service(name)
            for name in params.service_names
            }
        result = self._fn(*args, **kw, **service_kw)
        self._add_constructor(params, result)
        return result

    def _deduce_piece_t(self, params, name_list):
        for name in name_list:
            try:
                piece = params.values[name]
                break
            except KeyError:
                pass
        else:
            names_str = " or ".join(name_list)
            self._raise_error(f"{names_str} argument is expected for CRUD function: {list(params.values)}")
        return (name, deduce_t(piece))

    def _pick_model_ui_t(self, model_t):
        visualizer_reg = self._system['visualizer_reg']
        ui_t, fn_ref = visualizer_reg(model_t)
        return ui_t

    @staticmethod
    def _get_item_t(ui_t):
        if isinstance(ui_t, (
                htypes.model.index_list_ui_t,
                htypes.model.key_list_ui_t,
                htypes.model.index_tree_ui_t)):
            item_t = pyobj_creg.invite(ui_t.item_t)
        else:
            raise RuntimeError(f"Not supported model UI type: {ui_t}. Only list and tree are supported")
        if not isinstance(item_t, TRecord):
            raise RuntimeError(f"Model item type is expected to be a record: {item_t}")
        return item_t

    def _pick_key_fields(self, item_t, params):
        fields = []
        for name in params.ctx_names:
            if name in {'piece', 'model', 'value'}:
                continue
            if name in item_t.fields:
                fields.append(name)
        if not fields:
            available_fields = ", ".join(item_t.fields)
            log.warning(
                "%s/%s: No key fields are used (available fields: %s)",
                self._module_name, self._fn, available_fields)
        return fields

    def _template_ctr_kw(self, params):
        model_field, model_t = self._deduce_piece_t(params, ['piece', 'model'])
        ui_t = self._pick_model_ui_t(model_t)
        item_t = self._get_item_t(ui_t)
        key_fields = self._pick_key_fields(item_t, params)
        return dict(
            module_name=self._module_name,
            attr_qual_name=params.real_qual_name(self._fn),
            model_t=model_t,
            action_name=self._action_name,
            key_fields=tuple(key_fields),
            ctx_params=params.ctx_names,
            service_params=params.service_names,
            )

    def _add_constructor(self, params, result):
        ctr = self._make_constructor(params, result)
        self._ctr_collector.add_constructor(ctr)


class CrudInitProbe(CrudProbe):

    def _make_constructor(self, params, result):
        result_t = deduce_t(result)
        if not isinstance(result_t, TRecord):
            raise RuntimeError(f"Result of {self._action} action should be a record, but is: {result_t}")
        return CrudInitTemplateCtr(
            **self._template_ctr_kw(params),
            value_t=result_t,
            )


class CrudCommitProbe(CrudProbe):

    def __init__(self, system_probe, ctr_collector, module_name, action_name, fn, init_action_name):
        super().__init__(system_probe, ctr_collector, module_name, action_name, fn)
        self._init_action_name = init_action_name

    def _make_constructor(self, params, result):
        return CrudCommitTemplateCtr(
            **self._template_ctr_kw(params),
            init_action_name=self._init_action_name,
            )


class CrudDecorator:

    def __init__(self, system_probe, ctr_collector, module_name, action_name):
        self._system = system_probe
        self._ctr_collector = ctr_collector
        self._module_name = module_name
        self._action_name = action_name


class CrudInitDecorator(CrudDecorator):

    def __init__(self, system_probe, ctr_collector, module_name, action_name='get'):
        super().__init__(system_probe, ctr_collector, module_name, action_name)

    def __getattr__(self, action_name):
        return CrudInitDecorator(self._system, self._ctr_collector, self._module_name, action_name)

    def __call__(self, fn):
        check_not_classmethod(fn)
        check_is_function(fn)
        return CrudInitProbe(self._system, self._ctr_collector, self._module_name, self._action_name, fn)


class CrudCommitDecorator(CrudDecorator):

    def __init__(self, system_probe, ctr_collector, module_name, action_name='update', init_action_name=None):
        super().__init__(system_probe, ctr_collector, module_name, action_name)
        self._init_action_name = init_action_name

    def __getattr__(self, action_name):
        return CrudCommitDecorator(self._system, self._ctr_collector, self._module_name, action_name)

    def __call__(self, fn=None, *, init_action=None):
        if fn is None:
            if self._init_action_name:
                raise RuntimeError(f"Single argument, function is expected for CRUD decorator")
            return CrudCommitDecorator(
                self._system, self._ctr_collector, self._module_name, self._action_name, init_action_name=init_action)
        check_not_classmethod(fn)
        check_is_function(fn)
        return CrudCommitProbe(
            self._system, self._ctr_collector, self._module_name, self._action_name, fn, self._init_action_name)


class CrudMarker:

    def __init__(self, module_name, system, ctr_collector):
        self.get = CrudInitDecorator(system, ctr_collector, module_name)
        self.update = CrudCommitDecorator(system, ctr_collector, module_name)
