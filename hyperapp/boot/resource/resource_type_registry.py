from ..htypes.meta_type import list_mt, optional_mt, record_mt
from ..htypes.python_module import python_module_t
from ..htypes.file_data import file_data_t
from ..htypes.attribute import attribute_t
from ..htypes.partial import partial_t
from .list_mt_resource_type import ListMtResourceType
from .optional_mt_resource_type import OptionalMtResourceType
from .record_mt_resource_type import RecordMtResourceType
from .python_module import PythonModuleResourceType
from .file_data import FileDataType
from .attribute import AttributeResourceType
from .partial import PartialResourceType


def make_type_to_resource_type():
    return {
        list_mt: ListMtResourceType(),
        optional_mt: OptionalMtResourceType(),
        record_mt: RecordMtResourceType(),
        python_module_t: PythonModuleResourceType(),
        file_data_t: FileDataType(),
        attribute_t: AttributeResourceType(),
        partial_t: PartialResourceType(),
        }
