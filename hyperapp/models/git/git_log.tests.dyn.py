from datetime import datetime

from . import htypes
from .services import (
    mosaic,
    )
from .code.mark import mark
from .fixtures import feed_fixtures
from .fixtures import git_fixtures
from .tested.code import git_log


@mark.fixture
def head_commit():
    return htypes.git.commit(
        id='<unused>',
        short_id='<unused>',
        parents=(),
        time=datetime.fromtimestamp(0),
        author='<unused>',
        committer='<unused>',
        message='<unused>',
        )


@mark.fixture
def piece(repo_name, repo_dir, head_commit):
    return htypes.git.log_model(
        repo_name=repo_name,
        repo_dir=str(repo_dir),
        head_commit=mosaic.put(head_commit),
        )


async def test_model(repo_dir, repo_list, head_commit, piece):
    repo = repo_list.repo_by_dir(repo_dir)
    repo.head_log(head_commit).commit_list.append(head_commit)
    item_list = git_log.log_model(piece)
    assert item_list


def test_formatter(piece):
    title = git_log.format_model(piece)
    assert type(title) is str
