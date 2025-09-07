import logging
from datetime import datetime

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.mark import mark

log = logging.getLogger(__name__)


@mark.model
def log_model(piece, repo_list):
    repo = repo_list.repo_by_dir(piece.repo_dir)
    head_commit = web.summon(piece.head_commit)
    item_list = []
    for commit in repo.head_commits(head_commit):
        item = htypes.git.log_item(
            id_short=commit.short_id,
            dt=commit.time,
            author=commit.author,
            message=commit.message,
            )
        item_list.append(item)
    return item_list


@mark.actor.formatter_creg
def format_model(piece):
    return f"Git commits: {piece.repo_name}"
