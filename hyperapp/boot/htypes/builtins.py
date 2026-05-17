import logging

from .htypes import (
    tNone,
    tString,
    tBinary,
    tInt,
    tBool,
    tDateTime,
    )
from .hyper_ref import (
    ref_t,
    capsule_t,
    bundle_t,
    )
from .association import association_t
from .python_module import import_rec_t, python_module_t, import_rec_def_t, python_module_def_t
from .builtin_service import builtin_service_t
from .attribute import attribute_t, attribute_def_t
from .partial import partial_param_t, partial_param_def_t, partial_t, partial_def_t
from .raw import raw_t, raw_def_t

log = logging.getLogger(__name__)


_builtin_type_list = [
    tNone,
    tString,
    tBinary,
    tInt,
    tBool,
    tDateTime,
    ref_t,
    capsule_t,
    bundle_t,
    association_t,
    import_rec_t,
    python_module_t,
    import_rec_def_t,
    python_module_def_t,
    builtin_service_t,
    attribute_t,
    attribute_def_t,
    partial_param_t,
    partial_param_def_t,
    partial_t,
    partial_def_t,
    raw_t,
    raw_def_t,
    ]


def make_builtin_name_to_type():
    return {
        t.name: t
        for t in _builtin_type_list
        }
