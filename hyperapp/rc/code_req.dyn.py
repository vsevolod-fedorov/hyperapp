from dataclasses import dataclass

from . import htypes
from .services import (
    mosaic,
    )
from .code.path import Path


@dataclass(frozen=True)
class CodeReq:
    path: Path
    import_as: tuple[str]

    @classmethod
    def from_piece(cls, piece):
        return cls(
            path=Path.from_piece(piece.path),
            import_as=piece.import_as,
            )

    # Returns (import_path, module_target); import_path is the import_as prefix naming the module.
    def find_import_target(self, targets):
        # import_as is ('code', *module_path, *attr_path); Try longest module path first.
        sub_path = self.import_as[1:]
        for idx in range(len(sub_path), 0, -1):
            try:
                module = targets.find_nearest_module(self.path, sub_path[:idx])
            except KeyError:
                continue
            return (self.import_as[:idx + 1], module.module_tgt)
        raise KeyError(f"{self.path}: Module not found for import: {'.'.join(self.import_as)}")

    def resolve_to_import(self, import_path, target):
        rec = htypes.builtin.import_rec(
            full_name='.'.join(import_path),
            resource=mosaic.put(target.result),
            )
        return htypes.builtin.imports(
            pyobj=(rec,),
            raw=(),
            )
