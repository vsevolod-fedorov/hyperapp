
from .code.path import Path
from .code.target.state import TargetState


class TargetSet:

    def __init__(self, projects, module_list):
        self._projects = projects
        self._path_to_module = {module.path: module for module in module_list}
        self._name_to_target = {}

    def __len__(self):
        return len(self._name_to_target)

    def __iter__(self):
        return iter(self._name_to_target.values())

    def __getitem__(self, name):
        return self._name_to_target[name]

    def __setitem__(self, name, target):
        self._name_to_target[name] = target

    def enum_runnable(self):
        for tgt in self._name_to_target.values():
            if tgt.state == TargetState.RUNNABLE:
                yield tgt

    def find_nearest_module(self, from_path, sub_path):
        module_dir = from_path.path[:-1]
        for idx in range(len(module_dir), -1, -1):
            module = self._path_to_module.get(Path(from_path.project, (*module_dir[:idx], *sub_path)))
            if module:
                return module
        if len(sub_path) > 1:
            # Check if sub_path starts with name of a project imported by from_path project.
            project = self._projects[from_path.project]
            project_name = project.imports.get(sub_path[0])
            if project_name:
                module = self._path_to_module.get(Path(project_name, sub_path[1:]))
                if module:
                    return module
        raise KeyError(f"{from_path}: Module not found: {'/'.join(sub_path)}")
