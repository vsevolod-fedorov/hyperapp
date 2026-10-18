from collections import defaultdict

import yaml

from .services import (
    deduce_t,
    pyobj_creg,
    resource_type_producer,
    web,
    )


def _path_str(path):
    return '/'.join(path)


# Make shortest reference string to a name from resource file at location, as resource loader resolves it.
def _name_ref(projects, location, name_tuple):
    project_name, path = location
    target_project_name, target_path, name = name_tuple
    if target_project_name == 'builtin':
        return f'builtin:{_path_str(target_path)}:{name}'
    if target_project_name != project_name:
        imports = projects[project_name].imports
        try:
            local_name = next(local for local, global_name in imports.items() if global_name == target_project_name)
        except StopIteration:
            raise RuntimeError(
                f"{project_name}:{_path_str(path)}: Project {target_project_name!r} is not imported, but referred:"
                f" {target_project_name}:{_path_str(target_path)}:{name}")
        return f'{local_name}:{_path_str(target_path)}:{name}'
    if target_path == path:
        return name
    dir = path[:-1]
    if target_path[:len(dir)] == dir:
        # Relative to the directory of the resource file.
        return f'{_path_str(target_path[len(dir):])}:{name}'
    return f':{_path_str(target_path)}:{name}'


def _definition(projects, piece_to_name, location, piece):

    def resolver(ref):
        return _name_ref(projects, location, piece_to_name[web.summon(ref)])

    t = deduce_t(piece)
    resource_type = resource_type_producer(t)
    definition = resource_type.reverse_resolve(piece, resolver, None)
    type_name = piece_to_name[pyobj_creg.actor_to_piece(t)]
    return {
        'type': _name_ref(projects, location, type_name),
        'value': resource_type.to_dict(definition),
        }


def _module_text(projects, piece_to_name, location, name_to_piece):
    blocks = []
    for name, piece in sorted(name_to_piece.items()):
        data = {name: _definition(projects, piece_to_name, location, piece)}
        text = yaml.dump(data, sort_keys=False)
        blocks.append(''.join(f'  {line}' for line in text.splitlines(keepends=True)))
    # Blank lines between definitions, like in manually written files.
    return 'definitions:\n\n' + '\n'.join(blocks)


# Make resource module (.resources.yaml) texts.
# projects: project name -> workspace project, for its imports.
# piece_to_name: piece -> (project_name, path, name), for written pieces and all pieces they refer to.
# locations: (project_name, path) for resource files to make; each gets all pieces named there.
# Returns (project_name, path) -> text.
def dump_resource_modules(projects, piece_to_name, locations):
    location_to_name_to_piece = defaultdict(dict)
    for piece, (project_name, path, name) in piece_to_name.items():
        if (project_name, path) in locations:
            location_to_name_to_piece[project_name, path][name] = piece
    return {
        location: _module_text(projects, piece_to_name, location, location_to_name_to_piece[location])
        for location in locations
        }
