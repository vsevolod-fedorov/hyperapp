from dataclasses import dataclass

from . import htypes
from .services import (
    mosaic,
    )
from .code.import_dep import ImportDep, UnresolvedImportError
from .code.path import Path
from .code.target.type import TypeTarget

# The one job/type_req is registered for, in worker_config.resources.yaml.
TYPE_IMPORT_PREFIX = ('htypes',)


# Import of a type, as htypes.<type module name>.<type name>.
@dataclass(frozen=True)
class TypeReq:
    path: Path
    prefix: tuple[str]
    import_as: tuple[str]

    @classmethod
    def from_piece(cls, piece):
        return cls(
            path=Path.from_piece(piece.path),
            prefix=piece.prefix,
            import_as=piece.import_as,
            )

    def resolve(self, targets):
        type_path_len = len(self.prefix) + 2
        # Longer import path is an attribute of the type: it is recorded when the type is not resolved yet.
        if len(self.import_as) < type_path_len:
            raise UnresolvedImportError(f"{self.path}: Type name is missing for import: {'.'.join(self.import_as)}")
        module_name, type_name = self.import_as[len(self.prefix):type_path_len]
        try:
            name_tuple, piece = targets.find_type(self.path, module_name, type_name)
        except KeyError as x:
            raise UnresolvedImportError(f"{self.path}: {x.args[0]} for import: {'.'.join(self.import_as)}")
        return ImportDep(self.import_as[:type_path_len], TypeTarget.ensure(targets, name_tuple, piece))


# Types are loaded resources, so all ones seen by a module are given to its import recorders up front.
# Types used are still recorded, giving requirements, so module resources get just these.
# Using a type does not make import or test run incomplete, so no job is run again for types.
def type_cfg_items(targets, path):
    return [
        htypes.import_recorder.import_cfg_item(
            import_path=(*TYPE_IMPORT_PREFIX, module_name, type_name),
            resource=mosaic.put(piece),
            )
        for module_name, type_name, piece in targets.visible_types(path)
        ]
