from .services import (
    deduce_t,
    pyobj_creg,
    web,
    )
from .code.actor_ctr import ActorTemplateCtr
from .code.probe import ProbeBase
from .code.marker_utils import split_actor_params


class ActorProbeBase(ProbeBase):

    def __init__(self, system_probe, ctr_collector, module_name, fn, t=None):
        super().__init__(system_probe, ctr_collector, module_name, fn)
        self._t = t
        system_probe.add_global(self)

    def migrate_to(self, system_probe):
        self._system = system_probe
        self._ctr_collector = system_probe.resolve_service('ctr_collector')

    def __call__(self, *args, **kw):
        params = split_actor_params(self.real_fn, args, kw)
        if len(params.ctx_names) < 1 or params.ctx_names[0] != 'piece':
            raise RuntimeError(f"First parameter expected to be a 'piece': {self.real_fn!r}: {params.ctx_names!r}")
        piece = params.values[params.ctx_names[0]]
        if self._t is None:
            t = deduce_t(piece)
        else:
            t = self._t
        self._add_constructor(params, t)
        service_kw = {
            name: self._system.resolve_service(name)
            for name in params.service_names
            }
        return self._fn(*args, **kw, **service_kw)


class ActorProbe(ActorProbeBase):

    def __init__(self, system_probe, ctr_collector, module_name, service_name, fn, t=None):
        super().__init__(system_probe, ctr_collector, module_name, fn, t)
        self._service_name = service_name

    def _add_constructor(self, params, t):
        ctr = ActorTemplateCtr(
            module_name=self._module_name,
            attr_qual_name=params.real_qual_name(self.real_fn),
            service_name=self._service_name,
            t=t,
            creg_params=params.ctx_names,
            service_params=params.service_names,
            )
        self._ctr_collector.add_constructor(ctr)


def resolve_actor_probe_cfg_value(piece, key, system, service_name):
    fn = pyobj_creg.invite(piece.function)
    assert (
        isinstance(fn, ActorProbe)
        or hasattr(fn, '__self__') and isinstance(fn.__func__, ActorProbe)
        ) , repr(fn)
    return fn
