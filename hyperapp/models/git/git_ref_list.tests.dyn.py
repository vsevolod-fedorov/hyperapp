from datetime import datetime

from . import htypes
from .services import (
    mosaic,
    )
from .code.mark import mark
from .fixtures import git_fixtures
from .tested.code import git_ref_list


@mark.fixture
def piece(repo_name, repo_dir):
    return htypes.git.ref_list_model(
        repo_name=repo_name,
        repo_dir=str(repo_dir),
        )


def test_model(piece):
    result = git_ref_list.ref_list(piece)
    assert len(result) == 1


def test_log(piece):
    commit = htypes.git.commit(
        id='<unused>',
        short_id='<unused>',
        parents=(),
        time=datetime.fromtimestamp(0),
        author='<unused>',
        committer='<unused>',
        message='<unused>',
        )
    current_item = htypes.git.ref_item(
        name='<unused>',
        commit_id_short='<unused>',
        commit_dt=datetime.fromtimestamp(0),
        commit_author='<unused>',
        commit=mosaic.put(commit),
        )
    result = git_ref_list.ref_log(piece, current_item)
    assert result


def test_formatter(piece):
    title = git_ref_list.format_model(piece)
    assert type(title) is str
