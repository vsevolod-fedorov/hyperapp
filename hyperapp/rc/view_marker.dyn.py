from .code.marker_utils import (
    check_is_function,
    check_not_classmethod,
    )
from .code.actor_probe import ViewProbe


def view_marker(fn, module_name, system, ctr_collector):
    check_not_classmethod(fn)
    check_is_function(fn)
    return ViewProbe(system, ctr_collector, module_name, fn)
