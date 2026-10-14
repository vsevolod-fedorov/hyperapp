#!/usr/bin/env python3
# Print etags sections for resource definitions (*.resources.yaml) and types (*.types).
#
# Each definition gets several explicit tag names, so a resolved ref can be looked up exactly:
#   name                          - bare name
#   repo/path/module:name         - module path relative to the repo root
#   project:path/module:name      - absolute ref, for every project containing the file
#   :path/module:name             - absolute ref with empty (current) project
# Types modules are named with '.t' suffix: 'foo.types' -> 'foo.t'.

import re
import sys
from pathlib import Path

import yaml


RESOURCE_DEF_RE = re.compile(r'^  ([A-Za-z0-9_.-]+):')
TYPE_DEF_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*) *=')


def iter_files(root, suffix):
    for path in sorted(root.rglob(f'*{suffix}')):
        if '.git' not in path.relative_to(root).parts:
            yield path


def load_projects(root):
    projects = set()  # (name, project root dir)
    for file_name in ['projects.yaml', 'workspace.yaml']:
        for path in iter_files(root, file_name):
            if path.name != file_name:
                continue
            try:
                data = yaml.safe_load(path.read_text())
                items = data['projects'].items()
            except Exception as x:
                print(f"{path}: Skipping: {x}", file=sys.stderr)
                continue
            for key, info in items:
                project_dir = (path.parent / info['path']).resolve()
                for name in {key, info.get('local_name', key)}:
                    projects.add((name, project_dir))
    return projects


def module_names(root, projects, module_path):
    abs_path = module_path.resolve()
    yield module_path.relative_to(root).as_posix()
    for name, project_dir in sorted(projects):
        if abs_path.is_relative_to(project_dir):
            rel_path = abs_path.relative_to(project_dir).as_posix()
            yield f'{name}:{rel_path}'
            yield f':{rel_path}'


def tag_section(root, projects, path, module_path, def_re):
    names = list(dict.fromkeys(module_names(root, projects, module_path)))
    entries = []
    offset = 0
    for lineno, line in enumerate(path.read_bytes().splitlines(keepends=True), 1):
        text = line.decode()
        m = def_re.match(text)
        if m:
            name = m.group(1)
            pattern = text[:m.end(1)]
            for tag in [name, *(f'{module}:{name}' for module in names)]:
                entries.append(f'{pattern}\x7f{tag}\x01{lineno},{offset}\n')
        offset += len(line)
    body = ''.join(entries).encode()
    header = f'\x0c\n{path.relative_to(root).as_posix()},{len(body)}\n'.encode()
    return header + body


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    projects = load_projects(root)
    out = sys.stdout.buffer
    for path in iter_files(root, '.resources.yaml'):
        module_path = path.with_name(path.name.removesuffix('.resources.yaml'))
        out.write(tag_section(root, projects, path, module_path, RESOURCE_DEF_RE))
    for path in iter_files(root, '.types'):
        module_path = path.with_name(path.name.removesuffix('.types') + '.t')
        out.write(tag_section(root, projects, path, module_path, TYPE_DEF_RE))


if __name__ == '__main__':
    main()
