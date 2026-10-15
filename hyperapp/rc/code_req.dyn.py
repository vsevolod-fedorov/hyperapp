from dataclasses import dataclass

from .code.path import Path


@dataclass
class CodeReq:
    path: Path
    import_as: tuple[str]

    @classmethod
    def from_piece(cls, piece):
        return cls(
            path=Path.from_piece(piece.path),
            import_as=piece.import_as,
            )

    def get_target(self, targets):
        # import_as is ('code', *module_path, *attr_path); Try longest module path first.
        sub_path = self.import_as[1:]
        for idx in range(len(sub_path), 0, -1):
            try:
                module = targets.find_nearest_module(self.path, sub_path[:idx])
            except KeyError:
                continue
            return module.module_tgt
        raise KeyError(f"{self.path}: Module not found for import: {'.'.join(self.import_as)}")
