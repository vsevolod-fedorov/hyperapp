#!/usr/bin/env python3

import sys
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import yaml

from hyperapp.boot.htypes.builtins import make_builtin_name_to_type
from hyperapp.boot.htypes.meta_type import (
    make_meta_type_name_to_type,
    add_types_to_pyobj_creg_cache,
    register_builtin_mt,
    register_pyobj_creg_mt_actors,
    )
from hyperapp.boot.mosaic import Mosaic
from hyperapp.boot.web import Web
from hyperapp.boot.pyobj_registry import PyObjRegistry
from hyperapp.boot.association_registry import AssociationRegistry
from hyperapp.boot.python_importer import PythonImporter
from hyperapp.boot.resource.resource_type import ResourceType
from hyperapp.boot.resource.resource_type_registry import make_type_to_resource_type
from hyperapp.boot.resource.resource_type_producer import produce_resource_type
from hyperapp.boot.resource.pyobj_registry import register_pyobj_creg_actors
from hyperapp.boot.resource.builtin_service import make_builtin_name_to_service
from hyperapp.boot.resource.loader import load_file_tree, load_resources, add_source_paths
from hyperapp.boot.register_coders import register_coders
from hyperapp.boot.unbundler import Unbundler


def init_services(pyobj_creg, mosaic, web, python_importer, source_path, builtin_name_to_type, builtin_name_to_service):
    pyobj_creg.init(mosaic, web)
    add_types_to_pyobj_creg_cache(pyobj_creg, builtin_name_to_type)
    register_builtin_mt(mosaic, pyobj_creg)
    register_pyobj_creg_mt_actors(pyobj_creg)
    register_pyobj_creg_actors(pyobj_creg, mosaic, web, python_importer, source_path, builtin_name_to_service)
    register_coders()


def boot_services():
    reconstructors = []
    pyobj_creg = PyObjRegistry(config={}, reconstructors=reconstructors)
    mosaic = Mosaic(pyobj_creg)
    web = Web(mosaic, pyobj_creg)
    source_path = {}
    association_reg = AssociationRegistry()
    unbundler = Unbundler(web, mosaic, association_reg)
    builtin_name_to_type = {
        **make_builtin_name_to_type(),
        **make_meta_type_name_to_type(),
        }
    builtin_name_to_service = make_builtin_name_to_service(
        reconstructors,
        pyobj_creg,
        mosaic,
        web,
        source_path,
        association_reg,
        unbundler,
        )
    python_importer = PythonImporter()
    init_services(
        pyobj_creg,
        mosaic,
        web,
        python_importer,
        source_path,
        builtin_name_to_type,
        builtin_name_to_service,
        )
    resource_type_factory = partial(ResourceType, mosaic, web, pyobj_creg)
    type_to_resource_type = make_type_to_resource_type()
    resource_type_producer = partial(produce_resource_type, resource_type_factory, type_to_resource_type)
    return SimpleNamespace(
        pyobj_creg=pyobj_creg,
        mosaic=mosaic,
        source_path=source_path,
        builtin_name_to_type=builtin_name_to_type,
        builtin_name_to_service=builtin_name_to_service,
        resource_type_producer=resource_type_producer,
        unbundler=unbundler,
        )


def load_projects_resources(
        pyobj_creg,
        mosaic,
        source_path,
        builtin_name_to_type,
        builtin_name_to_service,
        resource_type_producer,
        projects_path,
        ):
    projects_dir = projects_path.parent
    project_to_path = yaml.safe_load(projects_path.read_text())
    project_to_files = {
        name: load_file_tree(projects_dir / path)
        for name, path in project_to_path.items()
        }
    resources, sources = load_resources(
        pyobj_creg, mosaic, builtin_name_to_type, builtin_name_to_service, resource_type_producer, project_to_files)
    add_source_paths(projects_dir, project_to_path, sources, source_path)
    return resources


def parse_path(resource_path):
    project_name, path_str, name = resource_path.split(':')
    path = tuple(path_str.split('/'))
    return (project_name, path, name)


def load(svc, projects_path, main_path):
    resources = load_projects_resources(
        svc.pyobj_creg,
        svc.mosaic,
        svc.source_path,
        svc.builtin_name_to_type,
        svc.builtin_name_to_service,
        svc.resource_type_producer,
        projects_path,
        )
    resource_path = parse_path(main_path)
    main_piece = resources[resource_path]
    main = svc.pyobj_creg.animate(main_piece)
    return main


def boot(projects_path, main_path):
    svc = boot_services()
    return load(svc, projects_path, main_path)


if __name__ == '__main__':
    projects_path = Path(sys.argv[1])
    main_path = sys.argv[2]
    args = sys.argv[3:]
    main = boot(projects_path, main_path)
    result = main(args)
    if type(result) is int or result is None:
        sys.exit(result)  # Result is exit code.
    if not result:
        sys.exit(100)
