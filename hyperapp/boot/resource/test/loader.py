import logging
import pytest
from pathlib import Path

from hyperapp.boot.resource.loader import load_file_tree, load_resources, add_source_paths

log = logging.getLogger(__name__)


@pytest.fixture
def test_dir():
    return Path(__file__).parent.resolve()


@pytest.fixture
def loader(
        pyobj_creg,
        mosaic,
        source_path,
        builtin_name_to_type,
        builtin_name_to_service,
        resource_type_producer,
        resources_dir,
        ):
    def load(project_to_path):
        project_to_files = {
            name: load_file_tree(resources_dir / path)
            for name, path in project_to_path.items()
            }
        resources, sources = load_resources(
            pyobj_creg, mosaic, builtin_name_to_type, builtin_name_to_service, resource_type_producer, project_to_files)
        for name, piece in resources.items():
            log.info("Loaded piece: %s -> %r", name, piece)
        for piece, project_name_path_source in sources.items():
            log.info("Loaded source: %r -> %r", piece, project_name_path_source)
        add_source_paths(resources_dir, project_to_path, sources, source_path)
        return resources, sources
    return load
