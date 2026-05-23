import logging
from collections import namedtuple
from functools import partial
from pathlib import Path

import yaml

from .source import ResourceModuleSource, TextSource


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


def _is_resource_path(path):
    return path[-1].endswith(RESOURCE_EXT)


def _file_path_to_resource_path(path):
    fname = path[-1]
    name = fname[:-len(RESOURCE_EXT)]
    return (*path[:-1], name)


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
    def from_full_name(cls, projects, full_name):
        proj_name, path, _ = full_name
        return cls(projects, proj_name, path)

    def __init__(self, projects, proj_name, path):
        self._projects = projects
        self._proj_name = proj_name
        self._path = path

    def __repr__(self):
        return f"@{self._proj_name}:{'/'.join(self._path)}"

    def __str__(self):
        return f"{self._proj_name}: {'/'.join(self._path)}"

    def resolve(self, full_name):
        parts = full_name.split(':')
        return self._resolve(parts, description=full_name)

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
        bytes = self._projects[project_name][path]
        text = bytes.decode()
        sources = {
            text: (project_name, path, TextSource(text))
            }
        return (text, path, sources)  # TODO: Add project id.


class _ResourceLoader:

    _Definition = namedtuple('_Definition', 'type value')

    def __init__(self, pyobj_creg, mosaic, builtin_name_to_type, resource_type_producer, projects):
        self._pyobj_creg = pyobj_creg
        self._mosaic = mosaic
        self._resource_type_producer = resource_type_producer
        self._projects = projects  # project_name -> path_to_bytes
        self._proj_path_to_def = {}  # (project_name, path) -> definition
        self._full_name_to_definition = {}
        self._full_name_to_piece = _name_to_builtin_type_piece(pyobj_creg, builtin_name_to_type)
        self._piece_to_source = {}  # piece -> (project name, path, source)

    def load(self):
        for proj_name, path_to_bytes in self._projects.items():
            for path, bytes in path_to_bytes.items():
                if not _is_resource_path(path):
                    continue
                resource_path = _file_path_to_resource_path(path)
                self._load_module(proj_name, resource_path, bytes)
        full_name_to_piece = {
            full_name: self._resolve(full_name)
            for full_name in self._full_name_to_definition
            }
        return (full_name_to_piece, self._piece_to_source)

    def _load_module(self, proj_name, path, bytes):
        data = self._load_yaml(path, bytes)
        ctx = _Context(self._projects, proj_name, path)
        for name, contents in data.get('definitions', {}).items():
            definition = self._load_definition(ctx, name, contents)
            self._full_name_to_definition[(proj_name, path, name)] = definition

    def _load_yaml(self, path, bytes):
        loader = yaml.SafeLoader(bytes)
        loader.name = path
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()

    def _load_definition(self, ctx, name, data):
        log.debug("%s: Load %r: %s", ctx, name, data)
        try:
            type_name = data['type']
            value_dict = data['value']
        except KeyError as x:
            raise RuntimeError(f"{proj_name}: {'/'.join(path)}: definition {name!r} has no {x.args[0]!r} attribute")
        resource_t_piece = self._resolve_name(ctx, type_name)
        resource_t = self._pyobj_creg.animate(resource_t_piece)
        definition_t = self._resource_type_producer(resource_t)
        try:
            definition = definition_t.from_dict(value_dict)
        except Exception as x:
            raise RuntimeError(f"{ctx}: Error resolving definition {name}: {x}")
        return self._Definition(definition_t, definition)

    def _resolve_name(self, ctx, name):
        full_name = ctx.resolve(name)
        return self._resolve(full_name)

    def _resolve_name_to_ref(self, ctx, name):
        piece = self._resolve_name(ctx, name)
        return self._mosaic.put(piece)

    def _resolve(self, full_name):
        try:
            return self._full_name_to_piece[full_name]
        except KeyError:
            pass
        definition = self._full_name_to_definition[full_name]
        ctx = _Context.from_full_name(self._projects, full_name)
        resolver = partial(self._resolve_name_to_ref, ctx)
        piece, sources = definition.type.resolve(definition.value, resolver, ctx)
        self._full_name_to_piece[full_name] = piece
        project_name, path, name = full_name
        self._piece_to_source[piece] = (project_name, path, ResourceModuleSource(name))
        for src_piece, path_and_src in sources.items():
            self._piece_to_source[src_piece] = path_and_src
        return piece


def load_resources(pyobj_creg, mosaic, builtin_name_to_type, resource_type_producer, projects):
    loader = _ResourceLoader(pyobj_creg, mosaic, builtin_name_to_type, resource_type_producer, projects)
    return loader.load()
