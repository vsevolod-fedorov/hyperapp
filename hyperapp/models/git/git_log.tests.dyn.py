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
def piece(repo_name, repo_dir, repo_list):
    repo = repo_list.repo_by_dir(repo_dir)
    repo.load_git_heads()
    [(ref_name, head_commit)] = repo.heads
    return htypes.git.log_model(
        repo_name=repo_name,
        repo_dir=str(repo_dir),
        ref_name=ref_name,
        head_commit=mosaic.put(head_commit),
        )


async def test_model(repo_dir, repo_list, piece):
    repo = repo_list.repo_by_dir(repo_dir)
    data = git_log.log_model(piece)
    assert isinstance(data, htypes.git.log_model_data)
    assert data.commit_count == 1


def test_formatter(piece):
    title = git_log.format_model(piece)
    assert type(title) is str
