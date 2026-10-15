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
        module = targets.find_module(self.path, self.import_as[1:])
        return module.module_tgt
