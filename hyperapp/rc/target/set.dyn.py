
from .code.path import Path
from .code.target.state import TargetState, combined_state


class TargetSet:

    def __init__(self, projects, module_list):
        self._projects = projects
        self._path_to_module = {module.path: module for module in module_list}
        self._name_to_target = {}
        # Targets which states are being got, innermost last. One met again depends on itself: it would recurse forever.
        self._state_stack = []
        # Target set -> cycle met; states are got many times, so cycles are collected, to be reported once.
        self._cycles = {}

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

    # Target in a dependency cycle can never be resolved, so it is failed.
    # Cycle is, for example, a tested module imported by another one through an untested module:
    # that one is complete, so requires complete tested module, which waits for the test.
    def _dep_state(self, tgt):
        if tgt in self._state_stack:
            cycle = self._state_stack[self._state_stack.index(tgt):]
            self._cycles.setdefault(frozenset(cycle), [*cycle, tgt])
            return TargetState.FAILED
        self._state_stack.append(tgt)
        try:
            return tgt.state
        finally:
            self._state_stack.pop()

    # State of a target having no job of its own.
    def deps_state(self, deps):
        return combined_state(self._dep_state(tgt) for tgt in deps)

    # Cycles met when states were got, as target lists, first one repeated last.
    # Where a cycle is entered depends on set order, so each starts from its target having the least name,
    # and they are sorted: reported the same way each run.
    @property
    def cycles(self):
        cycles = []
        for cycle in self._cycles.values():
            path = cycle[:-1]
            idx = path.index(min(path, key=lambda tgt: tgt.name))
            path = [*path[idx:], *path[:idx]]
            cycles.append([*path, path[0]])
        return sorted(cycles, key=lambda cycle: [tgt.name for tgt in cycle])
