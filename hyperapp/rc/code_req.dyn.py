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

    def _find_module(self, targets):
        # import_as is ('code', *module_path, *attr_path); Try longest module path first.
        sub_path = self.import_as[1:]
        for idx in range(len(sub_path), 0, -1):
            try:
                module = targets.find_nearest_module(self.path, sub_path[:idx])
            except KeyError:
                continue
            return (self.import_as[:idx + 1], module)
        raise KeyError(f"{self.path}: Module not found for import: {'.'.join(self.import_as)}")

    def get_target(self, targets):
        _, module = self._find_module(targets)
        return module.module_tgt

    def resolve_to_import(self, targets):
        import_name, module = self._find_module(targets)
        rec = htypes.builtin.import_rec(
            full_name='.'.join(import_name),
            resource=mosaic.put(module.module_tgt.resource),
            )
        return htypes.builtin.imports(
            pyobj=(rec,),
            raw=(),
            )
