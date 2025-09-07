import pygit2

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.mark import mark
from .fixtures import git_fixtures
from .tested.code import git_repo_list


def test_open():
    piece = git_repo_list.open_repo_list()
    assert piece


@mark.fixture
def piece():
    return htypes.git.repo_list_model()


def test_model(repo_name, repo_dir, piece):
    item_list = git_repo_list.repo_list_model(piece)
    assert type(item_list) is list
    assert item_list == [
        htypes.git.repo_item(
            name=repo_name,
            path=str(repo_dir),
            current_branch='master',
            ),
        ]


def test_add(piece):
    path = htypes.fs.path(
        parts=('tmp', 'git-tests', 'phony-repo-2'),
        )
    name = git_repo_list.add(piece, path)
    assert name == 'phony-repo-2'


def test_remove(piece):
    result = git_repo_list.remove(piece, current_key='phony-repo-1')
    assert result


def test_refs(piece):
    current_item = htypes.git.repo_item(
        name='<unused>',
        path='/tmp/sample-path',
        current_branch='unused',
        )
    result = git_repo_list.refs(piece, current_item)
    assert isinstance(result, htypes.git.ref_list_model)


def test_formatter(piece):
    title = git_repo_list.format_model(piece)
    assert type(title) is str


def test_init_hook():
    git_repo_list.load_repositories()
