import logging
from functools import partial

from ..htypes.builtin_service import builtin_service_t
from ..htypes.deduce_value_type import deduce_value_type_with_list
from ..code_registry import CodeRegistry
from ..cached_code_registry import CachedCodeRegistry

log = logging.getLogger(__name__)


def make_builtin_name_to_service(reconstructors, pyobj_creg, mosaic, web, source_path, association_reg):
    return {
        'reconstructors': reconstructors,
        'pyobj_creg': pyobj_creg,
        'mosaic': mosaic,
        'web': web,
        'source_path': source_path,
        'code_registry_ctr': partial(CodeRegistry, pyobj_creg, web),
        'cached_code_registry_ctr': partial(CachedCodeRegistry, mosaic, pyobj_creg, web),
        'deduce_t': partial(deduce_value_type_with_list, pyobj_creg),
        'association_reg': association_reg,
        }


def builtin_service_name_to_piece(name):
    return builtin_service_t(name)


def builtin_service_pyobj(piece, builtin_name_to_service):
    return builtin_name_to_service[piece.name]
