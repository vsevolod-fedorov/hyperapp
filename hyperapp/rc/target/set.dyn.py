from collections import defaultdict

from .code.path import Path
from .code.target.state import TargetState, combined_state


# Loaded resource modules of builtin types, as resource refs name them: builtin:type:<name>.
BUILTIN_TYPE_MODULE = ('builtin', ('type',))
# And of boot services: builtin:service:<name>.
BOOT_SERVICE_MODULE = ('builtin', ('service',))
TYPE_MODULE_SUFFIX = '.t'


class TargetSet:

    # resources: loaded ones, name tuple -> piece. Types and boot services are got from them.
    def __init__(self, projects, module_list, resources):
        self._projects = projects
        self._path_to_module = {module.path: module for module in module_list}
        self._type_module_to_types = defaultdict(dict)  # (project name, path) -> type name -> piece.
        self._dir_to_type_modules = defaultdict(dict)  # (project name, dir path) -> type module name -> path.
        self._project_to_type_modules = defaultdict(set)  # project name -> (project name, path) set.
        self._boot_services = {}  # Service name -> piece.
        for (project_name, path, name), piece in resources.items():
            if (project_name, path) == BOOT_SERVICE_MODULE:
                self._boot_services[name] = piece
            elif (project_name, path) == BUILTIN_TYPE_MODULE:
                self._type_module_to_types[project_name, path][name] = piece
            elif path and path[-1].endswith(TYPE_MODULE_SUFFIX):
                self._type_module_to_types[project_name, path][name] = piece
                module_name = path[-1][:-len(TYPE_MODULE_SUFFIX)]
                self._dir_to_type_modules[project_name, path[:-1]][module_name] = path
                self._project_to_type_modules[project_name].add((project_name, path))
        self._dir_to_visible_type_modules = {}  # Cache: (project name, dir path) -> type module name -> module.
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

    # Type modules are found by their names like code ones, nearest to from_path, in its project;
    # 'builtin' one has builtin types. The nearest one is used even if it lacks a type, as code modules are.
    # Returns type module name -> (project name, path).
    def _visible_type_modules(self, from_path):
        key = (from_path.project, from_path.path[:-1])
        try:
            return self._dir_to_visible_type_modules[key]
        except KeyError:
            pass
        project_name, module_dir = key
        name_to_module = {}
        for idx in range(len(module_dir) + 1):  # Nearer ones override.
            for name, path in self._dir_to_type_modules[project_name, module_dir[:idx]].items():
                name_to_module[name] = (project_name, path)
        name_to_module['builtin'] = BUILTIN_TYPE_MODULE
        self._dir_to_visible_type_modules[key] = name_to_module
        return name_to_module

    # Type modules of projects imported by from_path project, as code ones of them are:
    # by project local name and type module path from its root. Local type module of that name shadows them.
    # Returns import path of type module, without the prefix -> (project name, path).
    def _imported_type_modules(self, from_path):
        local_modules = self._visible_type_modules(from_path)
        for local_name, project_name in self._projects[from_path.project].imports.items():
            if local_name in local_modules:
                continue
            for module in self._project_to_type_modules[project_name]:
                _project_name, path = module
                yield ((local_name, *path[:-1], path[-1][:-len(TYPE_MODULE_SUFFIX)]), module)

    # Yields (import path without the prefix, type piece) for every type seen from from_path.
    def visible_types(self, from_path):
        modules = [
            *(((module_name,), module) for module_name, module in self._visible_type_modules(from_path).items()),
            *self._imported_type_modules(from_path),
            ]
        for module_path, module in modules:
            for type_name, piece in self._type_module_to_types[module].items():
                yield ((*module_path, type_name), piece)

    # sub_path is import path without the prefix: type module name, type name, maybe attributes of the type;
    # for a type of an imported project, its local name and type module path go first.
    # Returns length of sub_path part naming the type, type name tuple, a key of loaded resources, and the type piece.
    def find_type(self, from_path, sub_path):
        module_path_to_module = {
            **{(module_name,): module for module_name, module in self._visible_type_modules(from_path).items()},
            **dict(self._imported_type_modules(from_path)),
            }
        for idx in range(len(sub_path) - 1, 0, -1):  # Longest type module path first.
            module = module_path_to_module.get(sub_path[:idx])
            if module:
                break
        else:
            raise KeyError("Type module not found")
        type_name = sub_path[idx]
        try:
            return (idx + 1, (*module, type_name), self._type_module_to_types[module][type_name])
        except KeyError:
            project_name, path = module
            raise KeyError(f"Type module {project_name}:{'/'.join(path)} has no type {type_name}")

    # Service name -> piece. Boot services are the same for all modules.
    @property
    def boot_services(self):
        return self._boot_services

    def find_boot_service(self, name):
        return self._boot_services[name]

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
