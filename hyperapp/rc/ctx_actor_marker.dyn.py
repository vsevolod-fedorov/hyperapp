import inspect

from hyperapp.boot.htypes import Type

from .code.actor_probe import CtxActorProbe
from .code.ctx_actor_ctr import CtxActorProbeCtr
from .code.marker_utils import (
    check_is_function,
    check_not_classmethod,
    is_cls_arg,
    )


class ServiceCtxActorDecorator:

    def __init__(self, system, ctr_collector, module_name, service_name, t):
        self._system = system
        self._ctr_collector = ctr_collector
        self._module_name = module_name
        self._service_name = service_name
        self._t = t

    def __call__(self, fn):
        assert not inspect.iscoroutinefunction(fn), fn  # TODO: Probe for coroutine functions.
        qual_name = fn.__qualname__.split('.')
        check_not_classmethod(fn)
        check_is_function(fn)
        ctr = CtxActorProbeCtr(
            module_name=self._module_name,
            attr_qual_name=qual_name,
            service_name=self._service_name,
            t=self._t,
            )
        self._ctr_collector.add_constructor(ctr)
        return CtxActorProbe(self._system, self._ctr_collector, self._module_name, self._service_name, fn, self._t)


class ServiceCtxActorMarker:

    def __init__(self, system_probe, ctr_collector, module_name, service_name):
        self._system = system_probe
        self._ctr_collector = ctr_collector
        self._module_name = module_name
        self._service_name = service_name

    def __call__(self, fn_or_t):
        if isinstance(fn_or_t, Type):
            # Type-specialized variant (@mark.ctx_actor.my_registry(my_type)).
            if self._service_name in {'config_ctl_creg', 'cfg_item_creg'}:
                # These actors have special handling in System.update_config causing referred modules be loaded
                # before marker are inited by test job. As result, their functions/methods are left unwrapped.
                raise RuntimeError(f"Type-specialized decorators for {self._service_name} actors are not supported")
            return ServiceCtxActorDecorator(self._system, self._ctr_collector, self._module_name, self._service_name, t=fn_or_t)
        check_not_classmethod(fn_or_t)
        check_is_function(fn_or_t)
        # Not type-specialized variant  (@mark.ctx_actor.my_registry).
        return CtxActorProbe(self._system, self._ctr_collector, self._module_name, self._service_name, fn=fn_or_t)


class CtxActorMarker:

    def __init__(self, module_name, system, ctr_collector):
        self._module_name = module_name
        self._system = system
        self._ctr_collector = ctr_collector

    def __getattr__(self, service_name):
        return ServiceCtxActorMarker(self._system, self._ctr_collector, self._module_name, service_name)
