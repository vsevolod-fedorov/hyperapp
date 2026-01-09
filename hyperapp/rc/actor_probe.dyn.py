from .services import (
    deduce_t,
    pyobj_creg,
    web,
    )
from .code.actor_ctr import ActorTemplateCtr
from .code.ctx_actor_ctr import CtxActorTemplateCtr
from .code.probe import ProbeBase
from .code.marker_utils import split_actor_params, split_ctx_actor_params


class ActorProbeBase(ProbeBase):

    def __init__(self, system_probe, ctr_collector, module_name, fn, t=None):
        super().__init__(system_probe, ctr_collector, module_name, fn)
        self._t = t
        system_probe.add_global(self)

    def migrate_to(self, system_probe):
        self._system = system_probe
        self._ctr_collector = system_probe.resolve_service('ctr_collector')

    def _call(self, *args, **kw):
        params = self._split_params(args, kw)
        if 'piece' in params.ctx_names:
            if params.ctx_names[0] != 'piece':
                raise RuntimeError(f"'piece' should be first parameter: {self.real_fn!r}: {params.ctx_names!r}")
            piece = params.values[params.ctx_names[0]]
            piece_t = deduce_t(piece)
            if self._t is not None and piece_t is not self._t:
                raise RuntimeError(
                    f"Actual type for 'piece' parameter does not match declared by decorator: {self.real_fn!r}:"
                    " actual: {piece_t}, declared: {self._t}"
                    )
        elif self._t is None:
            raise RuntimeError(f"Add 'piece' parameter or declare it's type in decorator: {self.real_fn!r}: {params.ctx_names!r}")
        else:
            piece_t = self._t
        self._add_constructor(params, piece_t)
        service_kw = {
            name: self._system.resolve_service(name)
            for name in params.service_names
            }
        return self._call_fn(params, args, kw, service_kw)

    def _split_params(self, args, kw):
        return split_actor_params(self.real_fn, args, kw)

    def _call_fn(self, params, args, kw, service_kw):
        return self._fn(*args, **kw, **service_kw)


class FnActorProbe(ActorProbeBase):

    def __call__(self, *args, **kw):
        return self._call(*args, **kw)


class ActorProbe(FnActorProbe):

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


class CtxActorProbe(ActorProbeBase):

    def __init__(self, system_probe, ctr_collector, module_name, service_name, fn, t=None):
        super().__init__(system_probe, ctr_collector, module_name, fn, t)
        self._service_name = service_name

    def __call__(self, *args, **kw):
        return self._call(*args, **kw)

    def call(self, *args, **kw):
        return self._call(*args, **kw)

    def _split_params(self, args, kw):
        return split_ctx_actor_params(self.real_fn, args, kw)

    def _call_fn(self, params, args, kw, service_kw):
        return self._fn(**params.values, **service_kw)

    def _add_constructor(self, params, t):
        ctr = CtxActorTemplateCtr(
            module_name=self._module_name,
            attr_qual_name=params.real_qual_name(self.real_fn),
            service_name=self._service_name,
            t=t,
            ctx_params=params.ctx_names,
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


def resolve_ctx_actor_probe_cfg_value(piece, key, system, service_name):
    fn = pyobj_creg.invite(piece.function)
    assert (
        isinstance(fn, CtxActorProbe)
        or hasattr(fn, '__self__') and isinstance(fn.__func__, CtxActorProbe)
        ) , repr(fn)
    return fn
