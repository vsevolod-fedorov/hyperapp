from pathlib import Path

import pygit2

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
