import logging
from collections import defaultdict

from hyperapp.common.htypes.legacy_type import legacy_type_t

log = logging.getLogger(__name__)


class LegacyTypeResourceModule:

    def __init__(self):
        self._name_to_piece = {}

    @property
    def name(self):
        return 'legacy_type'

    def __setitem__(self, name, type_piece):
        self._name_to_piece[name] = type_piece

    def __contains__(self, var_name):
        return var_name in self._name_to_piece

    def __getitem__(self, var_name):
        return self._name_to_piece[var_name]

    def __iter__(self):
        return iter(self._name_to_piece)

    @property
    def associations(self):
        return []


# Unused. TODO: Remove?
# def legacy_builtin_type_resource_loader(types, builtin_types):
#     name_to_module = defaultdict(LegacyTypeResourceModule)
#     for t in builtin_types.values():
#         type_ref = types.reverse_resolve(t)
#         type_piece = legacy_type_t(type_ref)
#         name_to_module[f'legacy_type.{t.module_name}'][t.name] = type_piece
#         log.info("Legacy type resource %s.%s: %s", t.module_name, t.name, type_piece)
#     return name_to_module


def convert_builtin_types_to_dict(types, builtin_types):
    name_to_module = defaultdict(dict)
    for t in builtin_types.values():
        type_ref = types.reverse_resolve(t)
        module_dict = name_to_module[t.module_name]
        module_dict[t.name] = type_ref
    return name_to_module


def load_legacy_type_resources(local_types):
    name_to_module = defaultdict(LegacyTypeResourceModule)
    for module_name, local_type_module in local_types.items():
        for name, type_ref in local_type_module.items():
            type_piece = legacy_type_t(type_ref)
            name_to_module[f'legacy_type.{module_name}'][name] = type_piece
            log.info("Legacy type resource %s.%s: %s", module_name, name, type_piece)
    return name_to_module


def legacy_type_pyobj(piece, types):
    return types.resolve(piece.type_ref)
