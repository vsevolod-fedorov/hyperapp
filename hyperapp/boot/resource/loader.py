import logging
from collections import namedtuple
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
            assert name_tuple[:2] == x.args[0][:2]
            if len(x.args[0]) == 3:
                assert name_tuple[2] == x.args[0][2]
                project_name, path, name = x.args[0]
                raise RuntimeError(f"{self!r}: Missing: {project_name}:{'/'.join(path)}:{name}")
            else:
                project_name, path = x.args[0]
                raise RuntimeError(f"{self!r}: Missing: {project_name}:{'/'.join(path)}")

    def resolve(self, name_tuple):
        return self._loader._resolve(name_tuple)

    def find_nearest_module(self, sub_path, name):
        idx = len(self._path)
        while idx > 0:
            idx -= 1
            path = (*self._path[:idx], *sub_path)
            if self._loader._has_name(self._project_name, path, name):
                return (self._project_name, path)
        # Check if we have this name in another module, if sub_path starts with that module name.
        if self._loader._has_name(path[0], path[1:], name):
            return (path[0], path[1:])
        raise KeyError(sub_path)

    def _resolve_parts(self, parts, description):
        if len(parts) > 3:
            raise RuntimeError(f"{self}: Malformed name: More than two colons: {description!r}")
        if len(parts) == 1:
            # No colons, module-local name.
            return (self._project_name, self._path, parts[0])
        if len(parts) == 2:
            # 1 colon, project-local relative name.
            rel_path = _split_path(parts[0])
            path = (*self._path[:-1], *rel_path)
            return (self._project_name, path, parts[1])
        if len(parts) == 3:  # 2 colons.
            path = _split_path(parts[1])
            if parts[0]:  # Full name.
                return (parts[0], path, parts[2])
            else:  # Project-local absolute name.
                return (self._project_name, path, parts[2])

    def get_text(self, full_name):
        parts = full_name.split(':')
        project_name, path, _ = self._resolve_parts((*parts, ''), description=full_name)
        try:
            bytes = self._loader._projects[project_name][path]
        except KeyError:
            raise RuntimeError(f"{self!r}: Missing: {project_name}:{'/'.join(path)}")
        text = bytes.decode()
        sources = {
            text: (project_name, path, TextSource(text))
            }
        return (text, project_name, path, sources)


class _ResourceLoader:

    _LoaderRec = namedtuple('_LoaderRec', 'loader file_path')

    def __init__(self, pyobj_creg, mosaic, builtin_name_to_type, builtin_name_to_service, resource_type_producer, projects):
        self._pyobj_creg = pyobj_creg
        self._mosaic = mosaic
        self._builtin_name_to_type = builtin_name_to_type
        self._resource_type_producer = resource_type_producer
        self._projects = projects  # project_name -> path_to_bytes
        self._project_and_path_to_loader = {}  # (project_name, path) -> _LoaderRec
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
                self._discover_loader(project_name, file_path)
        for project_name, path in self._project_and_path_to_loader:
            self._load_definitions(project_name, path)
        name_tuple_to_piece = {
            name_tuple: self._resolve(name_tuple)
            for name_tuple in self._name_tuple_to_definition
            }
        return (name_tuple_to_piece, self._piece_to_source)

    # def _has_module(self, project_name, path):
    #     return (project_name, path) in self._has_modules

    def _has_name(self, project_name, path, name):
        if (project_name, path, name) not in self._name_tuple_to_definition:
            try:
                self._load_definitions(project_name, path)
            except KeyError:
                return False
        return (project_name, path, name) in self._name_tuple_to_definition

    _loaders = {
        ResourceModuleLoader(),
        TypeModuleLoader(),
        }

    def _discover_loader(self, project_name, file_path):
        for loader in self._loaders:
            if not loader.applicable(file_path):
                continue
            path = loader.file_path_to_path(file_path)
            self._project_and_path_to_loader[project_name, path] = self._LoaderRec(
                loader=loader,
                file_path=file_path,
                )
            self._has_modules.add((project_name, path))

    def _resolve(self, name_tuple):
        try:
            return self._name_tuple_to_piece[name_tuple]
        except KeyError:
            pass
        try:
            definition = self._name_tuple_to_definition[name_tuple]
        except KeyError:
            project_name, path, _ = name_tuple
            if project_name == 'builtin':
                raise
            if (project_name, path) not in self._project_and_path_to_loader:
                raise KeyError((project_name, path))
            self._load_definitions(project_name, path)
            definition = self._name_tuple_to_definition[name_tuple]
        ctx = _Context.from_name_tuple(self, name_tuple)
        piece, sources = definition.resolve(ctx)
        self._name_tuple_to_piece[name_tuple] = piece
        self._piece_to_source.update(sources)
        return piece

    def _load_definitions(self, project_name, path):
        rec = self._project_and_path_to_loader[project_name, path]
        source_path = '/'.join(rec.file_path)
        bytes = self._projects[project_name][rec.file_path]
        ctx = _Context(self, project_name, path)
        for name, definition in rec.loader.load_definitions(
                self._pyobj_creg, self._mosaic, self._builtin_name_to_type, self._resource_type_producer,
                ctx, bytes, source_path):
            self._name_tuple_to_definition[(project_name, path, name)] = definition


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
