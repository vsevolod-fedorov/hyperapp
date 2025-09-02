from . import htypes
from .code.mark import mark
from .fixtures import git_fixtures
from .tested.code import git_ref_list


@mark.fixture
def piece(repo_dir):
    return htypes.git.ref_list_model(
        repo_dir=str(repo_dir),
        )


def test_model(piece):
    result = git_ref_list.ref_list(piece)
    assert len(result) == 1
