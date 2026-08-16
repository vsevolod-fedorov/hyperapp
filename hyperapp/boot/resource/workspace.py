from functools import cached_property
from pathlib import Path

import yaml
from pydantic.dataclasses import dataclass as pydantic_dataclass, Field


@pydantic_dataclass
class Project:
    path: Path
    local_name: str
    imports: dict[str, str] = Field(default_factory=dict)

    @cached_property
    def path_to_bytes(self):
        return load_file_tree(self.path)


@pydantic_dataclass
class Workspace:
    projects: dict[str, Project]

    @classmethod
    def from_yaml_file(cls, path):
        data = yaml.safe_load(path.read_text())
        self = cls(**data)
        base_dir = path.parent
        for project in self.projects.values():
            project.path = base_dir / project.path
        return self

    @classmethod
    def from_simple_dict(cls, dir, name_to_path):
        imports = {}
        projects = {}
        for name, path in name_to_path.items():
            projects[name] = Project(dir / path, name, imports)
            imports[name] = name
        return cls(projects)


# Returns dict: parts tuple -> bytes
def load_file_tree(dir):
    path_to_bytes = {}
    for path in dir.rglob('*'):
        if path.is_dir():
            continue
        if path.suffix == '.pyc':
            continue
        rel_path = path.relative_to(dir)
        if 'test' in rel_path.parts:
            continue  # Skip pytest subdirectories.
        path_to_bytes[tuple(rel_path.parts)] = path.read_bytes()
    return path_to_bytes
