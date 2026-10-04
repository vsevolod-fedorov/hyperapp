from dataclasses import dataclass


@dataclass
class Path:
    project: str
    path: tuple[str]

    def __str__(self):
      path_str = "/".join(self.path)
      return f"{self.project}:{path_str}"
