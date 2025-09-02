from enum import Enum

from hyperapp.boot.htypes.deduce_value_type import DeduceTypeError

from .services import (
    deduce_t,
    )
from .code.marker_utils import (
    check_is_function,
    check_not_classmethod,
    split_params,
    )
from .code.probe import ProbeBase
from .code.view_factory_ctr import ViewFactoryTemplateCtr


class ViewFactoryProbe(ProbeBase):

    class Kind(Enum):
        view = 'view'
        model_t = 'model_t'
        ui_t = 'ui_t'

    def __init__(self, system_probe, ctr_collector, module_name, fn, kind):
        self._system = system_probe
        self._ctr_collector = ctr_collector
        self._module_name = module_name
        self._fn = fn
        self._kind = kind
        system_probe.add_global(self)

    def migrate_to(self, system_probe):
        self._system = system_probe
        self._ctr_collector = system_probe.resolve_service('ctr_collector')

    def __call__(self, *args, **kw):
        params = split_params(self._fn, args, kw)
        service_kw = {
            name: self._system.resolve_service(name)
            for name in params.service_names
            }
        model_t = None
        ui_t_t = None
        if self._kind == self.Kind.view:
            pass
        elif self._kind == self.Kind.model_t:
            model_t = self._deduce_model_t(params)
        elif self._kind == self.Kind.ui_t:
            ui_t_t = self._deduce_ui_t_t(params)
        else:
            assert False, self._kind
        result = self._fn(*args, **kw, **service_kw)
        self._add_constructor(params, model_t, ui_t_t, result)
        return result

    def _deduce_model_t(self, params):
        if len(params.ctx_names) < 1 or params.ctx_names[0] != 'piece':
            raise RuntimeError(
                "First parameter for model_t view factory expected to be a 'piece':"
                f" {self.real_fn!r}: {params.ctx_names!r}")
        return deduce_t(params.values['piece'])

    def _deduce_ui_t_t(self, params):
        if len(params.ctx_names) < 1 or params.ctx_names[0] != 'piece':
            raise RuntimeError(
                "First parameter for ui_t view factory expected to be a 'piece':"
                f" {self.real_fn!r}: {params.ctx_names!r}")
        if 'system_fn' not in params.ctx_names:
            raise RuntimeError(
                "'system_fn' parameter is expected for ui_t view factory:"
                f" {self.real_fn!r}: {params.ctx_names!r}")
        return deduce_t(params.values['piece'])

    def _add_constructor(self, params, model_t, ui_t_t, result):
        try:
            result_t = deduce_t(result)
        except DeduceTypeError as x:
            raise RuntimeError(f"{self._fn}: Returned not a deducible data type: {result!r}") from x
        ctr = ViewFactoryTemplateCtr(
            module_name=self._module_name,
            attr_qual_name=params.real_qual_name(self._fn),
            model_t=model_t,
            ui_t_t=ui_t_t,
            ctx_params=params.ctx_names,
            service_params=params.service_names,
            view_t=result_t,
            )
        self._ctr_collector.add_constructor(ctr)


class Marker:

    def __init__(self, module_name, system, ctr_collector, kind):
        self._module_name = module_name
        self._system = system
        self._ctr_collector = ctr_collector
        self._kind = kind

    def __call__(self, fn):
        check_not_classmethod(fn)
        check_is_function(fn)
        return ViewFactoryProbe(
            self._system, self._ctr_collector, self._module_name, fn, self._kind)


class ViewFactoryMarker(Marker):

    def __init__(self, module_name, system, ctr_collector):
        super().__init__(module_name, system, ctr_collector, kind=ViewFactoryProbe.Kind.view)

    @property
    def model_t(self):
        return Marker(self._module_name, self._system, self._ctr_collector, kind=ViewFactoryProbe.Kind.model_t)

    @property
    def ui_t(self):
        return Marker(self._module_name, self._system, self._ctr_collector, kind=ViewFactoryProbe.Kind.ui_t)
