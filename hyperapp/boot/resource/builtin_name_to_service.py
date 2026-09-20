import logging
from functools import partial

from ..htypes.deduce_value_type import deduce_value_type_with_list
from ..code_registry import CodeRegistry
from ..cached_code_registry import CachedCodeRegistry
from .loader import load_resources

log = logging.getLogger(__name__)


def make_builtin_name_to_service(
        reconstructors,
        pyobj_creg,
        mosaic,
        web,
        source_path,
        assoc_implanters,
        unbundler,
        builtin_name_to_type,
        resource_type_producer,
        ):
    builtin_name_to_service = {
        'reconstructors': reconstructors,
        'pyobj_creg': pyobj_creg,
        'mosaic': mosaic,
        'web': web,
        'source_path': source_path,
        'code_registry_ctr': partial(CodeRegistry, pyobj_creg, web),
        'cached_code_registry_ctr': partial(CachedCodeRegistry, mosaic, pyobj_creg, web),
        'deduce_t': partial(deduce_value_type_with_list, pyobj_creg),
        'assoc_implanters': assoc_implanters,
        'unbundler': unbundler,
        }
    loader = partial(
        load_resources, pyobj_creg, mosaic, builtin_name_to_type, builtin_name_to_service, resource_type_producer)
    builtin_name_to_service['load_resources'] = loader
    return builtin_name_to_service
