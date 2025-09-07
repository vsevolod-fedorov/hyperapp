import inspect

from .code.probe import real_fn
from .code.marker_utils import split_actor_params
from .code.init_hook_ctr import InitHookCtr


class InitHookProbe:

    def __init__(self, system_probe, fn):
        self._system = system_probe
        self._fn = fn

    @property
    def real_fn(self):
        return real_fn(self._fn)

    def __call__(self):
        params = split_actor_params(self.real_fn, [], {})
        service_kw = {
            name: self._system.resolve_service(name)
            for name in params.service_names
            }
        return self._fn(**service_kw)


def init_hook_marker(fn, module_name, system, ctr_collector):
    ctr = InitHookCtr(
        module_name=module_name,
        attr_qual_name=fn.__qualname__.split('.'),
        service_params=tuple(inspect.signature(fn).parameters),
        )
    ctr_collector.add_constructor(ctr)
    return InitHookProbe(system, fn)
