from dataclasses import dataclass

from . import htypes
from .services import (
    mosaic,
    )
from .code.path import Path


# Requirement resolved to a module target. Reqs importing from the same module give equal deps.
@dataclass(frozen=True)
class CodeDep:
    import_path: tuple[str]  # import_as prefix naming the module.
    target: object

    def make_cfg_item(self):
        return htypes.import_recorder.import_cfg_item(
            import_path=self.import_path,
            resource=mosaic.put(self.target.result),
            )

    def make_import(self):
        rec = htypes.builtin.import_rec(
            full_name='.'.join(self.import_path),
            resource=mosaic.put(self.target.result),
            )
        return htypes.builtin.imports(
            pyobj=(rec,),
            raw=(),
            )


@dataclass(frozen=True)
class CodeReq:
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
        # import_as is (*prefix, *module_path, *attr_path); Try longest module path first.
        prefix_len = len(self.prefix)
        sub_path = self.import_as[prefix_len:]
        for idx in range(len(sub_path), 0, -1):
            try:
                module = targets.find_nearest_module(self.path, sub_path[:idx])
            except KeyError:
                continue
            return CodeDep(self.import_as[:prefix_len + idx], module.module_tgt)
        raise KeyError(f"{self.path}: Module not found for import: {'.'.join(self.import_as)}")
