import logging
from pathlib import Path

from ..htypes.python_module import python_module_t
from .source import TextSource
from .resource_module import ResourceModuleLoader
from .type_module import TypeModuleLoader
from .builtin_service import builtin_service_name_to_piece


log = logging.getLogger(__name__)


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


_builtin_project_name = 'builtin'
_builtin_type_path = ('type',)
_builtin_service_path = ('service',)


def _name_to_builtin_type_piece(pyobj_creg, name_to_type):
    return {
        (_builtin_project_name, _builtin_type_path, name): pyobj_creg.actor_to_piece(t)
        for name, t in name_to_type.items()
        }


def _name_to_builtin_service_piece(builtin_name_to_service):
    return {
        (_builtin_project_name, _builtin_service_path, name): builtin_service_name_to_piece(name)
        for name in builtin_name_to_service
        }


def _split_path(path):
    assert type(path) is str
    if path == '':
        return ()
    else:
        return tuple(path.split('/'))


class _Context:

    @classmethod
    def from_name_tuple(cls, loader, name_tuple):
        project_name, path, _ = name_tuple
        return cls(loader, project_name, path)

    def __init__(self, loader, project_name, path):
        self._loader = loader
        self._project_name = project_name
        self._path = path

    def __repr__(self):
        return f"@{self._project_name}:{'/'.join(self._path)}"

    def __str__(self):
        return f"{self._project_name}: {'/'.join(self._path)}"

    @property
    def project_name(self):
        return self._project_name

    @property
    def path(self):
        return self._path

    def resolve_to_ref(self, name):
        return self._loader._mosaic.put(self.resolve_name(name))

    def resolve_to_ref_opt(self, name):
        if name is None:
            return None
        return self._loader._mosaic.put(self.resolve_name(name))

    def resolve_name(self, name):
        parts = name.split(':')
        name_tuple = self._resolve_parts(parts, description=name)
        try:
            return self.resolve(name_tuple)
        except KeyError as x:
            raise RuntimeError(f"{self!r}: {x}")

    def resolve(self, name_tuple):
        return self._loader._resolve(name_tuple)

    def find_nearest_module(self, sub_path, name):
        idx = len(self._path)
        while idx > 0:
            idx -= 1
            path = (*self._path[:idx], *sub_path)
            if self._loader._has_name(self._project_name, path, name):
                return (self._project_name, path)
        raise KeyError(sub_path)

    def _resolve_parts(self, parts, description):
        if len(parts) > 3:
            raise RuntimeError(f"{self}: Malformed name: More than two colons: {description!r}")
        if len(parts) == 1:
            # No colons, module-local name.
            return (self._project_name, self._path, parts[0])
        if len(parts) == 2:
            # 1 colon, project-local name
            name_path = _split_path(parts[0])
            if len(name_path) > len(self._path):
                raise RuntimeError(f"{self}: Malformed name: Path is too deep: {description!r}")
            path = (*self._path[:len(self._path) - len(name_path)], *name_path)
            return (self._project_name, path, parts[1])
        if len(parts) == 3:
            # 2 colons, full name.
            return (parts[0], _split_path(parts[1]), parts[2])

    def get_text(self, full_name):
        parts = full_name.split(':')
        project_name, path, _ = self._resolve_parts((*parts, ''), description=full_name)
        bytes = self._loader._projects[project_name][path]
        text = bytes.decode()
        sources = {
            text: (project_name, path, TextSource(text))
            }
        return (text, project_name, path, sources)


class _ResourceLoader:

    def __init__(self, pyobj_creg, mosaic, builtin_name_to_type, builtin_name_to_service, resource_type_producer, projects):
        self._pyobj_creg = pyobj_creg
        self._mosaic = mosaic
        self._builtin_name_to_type = builtin_name_to_type
        self._resource_type_producer = resource_type_producer
        self._projects = projects  # project_name -> path_to_bytes
        self._name_tuple_to_definition = {}
        self._name_tuple_to_piece = {
            **_name_to_builtin_type_piece(pyobj_creg, builtin_name_to_type),
            **_name_to_builtin_service_piece(builtin_name_to_service),
            }
        self._has_modules = {
            (_builtin_project_name, _builtin_type_path),
            (_builtin_project_name, _builtin_service_path),
            }
        self._piece_to_source = {}  # piece -> (project_name, path, source)

    def load(self):
        for project_name, path_to_bytes in self._projects.items():
            for file_path, bytes in path_to_bytes.items():
                self._load_module(project_name, file_path, bytes)
        name_tuple_to_piece = {
            name_tuple: self._resolve(name_tuple)
            for name_tuple in self._name_tuple_to_definition
            }
        return (name_tuple_to_piece, self._piece_to_source)

    _loaders = {
        ResourceModuleLoader(),
        TypeModuleLoader(),
        }

    def _load_module(self, project_name, file_path, bytes):
        for loader in self._loaders:
            if not loader.applicable(file_path):
                continue
            path = loader.file_path_to_path(file_path)
            ctx = _Context(self, project_name, path)
            source_path = '/'.join(file_path)
            for name, definition in loader.load_definitions(
                    self._pyobj_creg, self._mosaic, self._builtin_name_to_type, self._resource_type_producer,
                    ctx, bytes, source_path):
                self._name_tuple_to_definition[(project_name, path, name)] = definition
                self._has_modules.add((project_name, path))

    # def _has_module(self, project_name, path):
    #     return (project_name, path) in self._has_modules

    def _has_name(self, project_name, path, name):
        return (project_name, path, name) in self._name_tuple_to_definition

    def _resolve(self, name_tuple):
        try:
            return self._name_tuple_to_piece[name_tuple]
        except KeyError:
            pass
        definition = self._name_tuple_to_definition[name_tuple]
        ctx = _Context.from_name_tuple(self, name_tuple)
        piece, sources = definition.resolve(ctx)
        self._name_tuple_to_piece[name_tuple] = piece
        self._piece_to_source.update(sources)
        return piece


def load_resources(pyobj_creg, mosaic, builtin_name_to_type, builtin_name_to_service, resource_type_producer, projects):
    loader = _ResourceLoader(pyobj_creg, mosaic, builtin_name_to_type, builtin_name_to_service, resource_type_producer, projects)
    return loader.load()


def add_source_paths(root_dir, project_to_path, sources, source_path):
    for piece in sources:
        if not isinstance(piece, python_module_t):
            continue
        project_name, path, src = sources[piece.source]
        project_path = root_dir / project_to_path[project_name]
        full_path = project_path.joinpath(*path)
        source_path[piece] = full_path
