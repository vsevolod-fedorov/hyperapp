from functools import partial

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.mark import mark
from .code.context import Context
from .code.system_fn import ContextFn
from .code import git_log
from .fixtures import git_fixtures
from .tested.code import git_log_adapter


@mark.fixture
def log_model_fn(rpc_system_call_factory, repo_list):
    return ContextFn(
        rpc_system_call_factory=rpc_system_call_factory,
        ctx_params=('piece',),
        service_params=('repo_list',),
        raw_fn=git_log.log_model,
        bound_fn=partial(git_log.log_model, repo_list=repo_list),
        )


@mark.fixture
def model(repo_name, repo_dir, repo_list):
    repo = repo_list.repo_by_dir(repo_dir)
    repo.load_git_heads()
    [(ref_name, head_commit)] = repo.heads
    return htypes.git.log_model(
        repo_name=repo_name,
        repo_dir=str(repo_dir),
        ref_name=ref_name,
        head_commit=mosaic.put(head_commit),
        )


@mark.fixture
def ctx():
    return Context()


def test_adapter(log_model_fn, model, ctx):
    accessor = htypes.accessor.model_accessor()
    adapter_piece = htypes.git.log_adapter(
        accessor=mosaic.put(accessor),
        system_fn=mosaic.put(log_model_fn.piece),
        )
    adapter = git_log_adapter.GitLogAdapter.from_piece(adapter_piece, model, ctx)

    assert adapter.column_count() == 4
    assert adapter.column_title(0) == 'author'
    assert adapter.column_title(1) == 'dt'
    assert adapter.row_count() == 1
    # assert adapter.cell_data(1, 0) == 22
    # assert adapter.cell_data(2, 1) == "third"


def test_factory(log_model_fn, model):
    accessor = htypes.accessor.model_accessor()
    ui_t = htypes.model.record_ui_t(
        record_t=pyobj_creg.actor_to_ref(htypes.git.log_model_data),
        )
    view = git_log_adapter.git_log_layout(ui_t, accessor, log_model_fn)
    assert isinstance(view, htypes.list.view)
