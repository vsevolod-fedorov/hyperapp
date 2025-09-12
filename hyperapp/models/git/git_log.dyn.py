import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.mark import mark
from .code.list_diff import IndexListDiff

log = logging.getLogger(__name__)


@mark.model
def log_model(piece, repo_list):
    repo = repo_list.repo_by_dir(piece.repo_dir)
    commit = web.summon(piece.head_commit)
    commit_count = 1
    while commit.parents:
        commit = web.summon(commit.parents[0])
        commit_count += 1
    return htypes.git.log_model_data(
        head_commit=piece.head_commit,
        commit_count=commit_count,
        )


@mark.actor.formatter_creg
def format_model(piece):
    return f"Git commits: {piece.repo_name}"
