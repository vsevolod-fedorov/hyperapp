from ..htypes.attribute import attribute_t
from ..htypes.partial import partial_t
from ..htypes.raw import raw_t
from ..htypes.python_module import python_module_t
from ..htypes.builtin_service import builtin_service_t
from .attribute import attribute_pyobj
from .partial import partial_pyobj
from .raw import raw_pyobj
from .python_module import python_module_pyobj
from .builtin_service import builtin_service_pyobj


def register_resources_at_pyobj_creg(pyobj_creg, mosaic, web, python_importer, builtin_name_to_service):
    pyobj_creg.register_actor(builtin_service_t, builtin_service_pyobj, builtin_name_to_service=builtin_name_to_service)
    pyobj_creg.register_actor(attribute_t, attribute_pyobj, pyobj_creg=pyobj_creg)
    pyobj_creg.register_actor(partial_t, partial_pyobj, pyobj_creg=pyobj_creg)
    pyobj_creg.register_actor(raw_t, raw_pyobj, web=web)
    pyobj_creg.register_actor(
        python_module_t, python_module_pyobj,
        mosaic=mosaic,
        python_importer=python_importer,
        pyobj_creg=pyobj_creg,
        )
