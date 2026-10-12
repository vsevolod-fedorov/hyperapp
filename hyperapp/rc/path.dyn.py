from dataclasses import dataclass

from . import htypes


@dataclass
class Path:
    project: str
    path: tuple[str]

    @classmethod
    def from_piece(cls, piece):
        return cls(piece.project, piece.path)

    def __str__(self):
        path_str = "/".join(self.path)
        return f"{self.project}:{path_str}"

    @property
    def piece(self):
        return htypes.path.path(
            project=self.project,
            path=self.path,
            )
