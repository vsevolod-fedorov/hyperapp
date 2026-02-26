from .code.marker_utils import (
    check_is_function,
    check_not_classmethod,
    )
from .code.selector_probe import SelectorOpenProbe, SelectorPickProbe


class SelectorDecorator:

    def __init__(self, system_probe, ctr_collector, module_name, probe_cls):
        self._system = system_probe
        self._ctr_collector = ctr_collector
        self._module_name = module_name
        self._probe_cls = probe_cls

    def __call__(self, fn):
        check_not_classmethod(fn)
        check_is_function(fn)
        return self._probe_cls(self._system, self._ctr_collector, self._module_name, fn)


class SelectorMarker:

    def __init__(self, module_name, system, ctr_collector):
        self._module_name = module_name
        self._system = system
        self._ctr_collector = ctr_collector

    @property
    def open(self):
        return SelectorDecorator(self._system, self._ctr_collector, self._module_name, SelectorOpenProbe)

    @property
    def pick(self):
        return SelectorDecorator(self._system, self._ctr_collector, self._module_name, SelectorPickProbe)
