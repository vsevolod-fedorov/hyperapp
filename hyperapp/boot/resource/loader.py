import logging
from pathlib import Path

from .source import ResourceModuleSource, TextSource
from .resource_module import load_resource_module_definitions


log = logging.getLogger(__name__)

RESOURCE_EXT = '.resources.yaml'


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


def _is_resource_file_path(file_path):
    return file_path[-1].endswith(RESOURCE_EXT)


def _file_path_to_path(file_path):
    fname = file_path[-1]
    name = fname[:-len(RESOURCE_EXT)]
    return (*file_path[:-1], name)


def _name_to_builtin_type_piece(pyobj_creg, name_to_type):
    return {
        ('builtin', ('type',), name): pyobj_creg.actor_to_piece(t)
        for name, t in name_to_type.items()
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
        proj_name, path, _ = name_tuple
        return cls(loader, proj_name, path)

    def __init__(self, loader, proj_name, path):
        self._loader = loader
        self._proj_name = proj_name
        self._path = path

    def __repr__(self):
        return f"@{self._proj_name}:{'/'.join(self._path)}"

    def __str__(self):
        return f"{self._proj_name}: {'/'.join(self._path)}"

    @property
    def proj_name(self):
        return self._proj_name

    @property
    def path(self):
        return self._path

    def resolve_to_ref(self, name):
        return self._loader._mosaic.put(self.resolve(name))

    def resolve(self, name):
        parts = name.split(':')
        name_tuple = self._resolve(parts, description=name)
        return self._loader._resolve(name_tuple)

    def _resolve(self, parts, description):
        if len(parts) > 3:
            raise RuntimeError(f"{self}: Malformed name: More than two colons: {description!r}")
        if len(parts) == 1:
            # No colons, module-local name.
            return (self._proj_name, self._path, parts[0])
        if len(parts) == 2:
            # 1 colon, project-local name
            name_path = _split_path(parts[0])
            if len(name_path) > len(self._path):
                raise RuntimeError(f"{self}: Malformed name: Path is too deep: {description!r}")
            path = (*self._path[:len(self._path) - len(name_path)], *name_path)
            return (self._proj_name, path, parts[1])
        if len(parts) == 3:
            # 2 colons, full name.
            return (parts[0], _split_path(parts[1]), parts[2])

    def get_text(self, full_name):
        parts = full_name.split(':')
        project_name, path, _ = self._resolve((*parts, ''), description=full_name)
        bytes = self._loader._projects[project_name][path]
        text = bytes.decode()
        sources = {
            text: (project_name, path, TextSource(text))
            }
        return (text, path, sources)  # TODO: Add project id.


class _ResourceLoader:

    def __init__(self, pyobj_creg, mosaic, builtin_name_to_type, resource_type_producer, projects):
        self._pyobj_creg = pyobj_creg
        self._mosaic = mosaic
        self._resource_type_producer = resource_type_producer
        self._projects = projects  # project_name -> path_to_bytes
        self._proj_path_to_def = {}  # (project_name, path) -> definition
        self._name_tuple_to_definition = {}
        self._name_tuple_to_piece = _name_to_builtin_type_piece(pyobj_creg, builtin_name_to_type)
        self._piece_to_source = {}  # piece -> (project name, path, source)

    def load(self):
        for proj_name, path_to_bytes in self._projects.items():
            for file_path, bytes in path_to_bytes.items():
                if not _is_resource_file_path(file_path):
                    continue
                path = _file_path_to_path(file_path)
                self._load_module(proj_name, path, bytes, file_path)
        name_tuple_to_piece = {
            name_tuple: self._resolve(name_tuple)
            for name_tuple in self._name_tuple_to_definition
            }
        return (name_tuple_to_piece, self._piece_to_source)

    def _load_module(self, proj_name, path, bytes, file_path):
        ctx = _Context(self, proj_name, path)
        for name, definition in load_resource_module_definitions(
                self._pyobj_creg, self._resource_type_producer, ctx, bytes, file_path):
            self._name_tuple_to_definition[(proj_name, path, name)] = definition

    def _resolve(self, name_tuple):
        try:
            return self._name_tuple_to_piece[name_tuple]
        except KeyError:
            pass
        definition = self._name_tuple_to_definition[name_tuple]
        ctx = _Context.from_name_tuple(self, name_tuple)
        piece, sources = definition.type.resolve(definition.value, ctx)
        self._name_tuple_to_piece[name_tuple] = piece
        project_name, path, name = name_tuple
        self._piece_to_source[piece] = (project_name, path, ResourceModuleSource(name))
        for src_piece, path_and_src in sources.items():
            self._piece_to_source[src_piece] = path_and_src
        return piece


def load_resources(pyobj_creg, mosaic, builtin_name_to_type, resource_type_producer, projects):
    loader = _ResourceLoader(pyobj_creg, mosaic, builtin_name_to_type, resource_type_producer, projects)
    return loader.load()
