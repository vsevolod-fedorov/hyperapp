from pathlib import Path
from unittest.mock import Mock

import pygit2

from . import htypes
from .code.mark import mark


@mark.fixture
def data_dir():
    return Path('/tmp/git-tests')


@mark.fixture.obj
def repo_name():
    return 'phony-repo-1'


@mark.fixture.obj
def repo_dir(data_dir, repo_name):
    dir = data_dir / repo_name
    if not dir.exists():
        pygit2.init_repository(dir)
        repo = pygit2.Repository(dir)
        path = dir / 'test-file.txt'
        path.write_text("Sample contents")
        repo.index.add(path.name)
        repo.index.write()
        tree = repo.index.write_tree()
        author = pygit2.Signature('Test Author', 'test@nothwere.tld')
        repo.create_commit('HEAD', author, author, "Test commit", tree, [])

    return dir


@mark.fixture
def file_bundle_factory(repo_dir, path, encoding):
    if path.stem.endswith('list'):
        storage = htypes.git.repo_list_storage(
            path_list=(str(repo_dir),),
            )
    elif path.stem.endswith('objects'):
        storage = htypes.git.storage(heads=())
    else:
        assert False, "Unexpected file bundle path: {path}"
    file_bundle = Mock()
    file_bundle.load_piece.return_value = storage
    return file_bundle
