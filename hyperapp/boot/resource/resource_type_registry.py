from ..htypes.meta_type import list_mt, optional_mt
from .python_module import python_module_t
from .attribute import attribute_t
from .call import call_t
from .partial import partial_t
from .list_mt_resource_type import ListMtResourceType
from .optional_mt_resource_type import OptionalMtResourceType
from .python_module import PythonModuleResourceType
from .attribute import AttributeResourceType
from .call import CallResourceType
from .partial import PartialResourceType


def make_type_to_resource_type():
    return {
        list_mt: ListMtResourceType(),
        optional_mt: OptionalMtResourceType(),
        python_module_t: PythonModuleResourceType(),
        attribute_t: AttributeResourceType(),
        call_t: CallResourceType(),
        partial_t: PartialResourceType(),
        }
