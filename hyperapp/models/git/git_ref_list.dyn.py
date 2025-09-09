import logging
from datetime import datetime

from . import htypes
from .services import (
    mosaic,
    )
from .code.mark import mark

log = logging.getLogger(__name__)


@mark.model
def ref_list(piece, repo_list):
    repo = repo_list.repo_by_dir(piece.repo_dir)
    item_list = []
    for ref in repo.repo.references.objects:
        object = ref.peel()
        log.info("Loading commits for: %s", object.id)
        old_count = repo.object_count
        commit = repo.get_commit(object)
        log.info("Loaded %d commits", repo.object_count - old_count)
        item = htypes.git.ref_item(
            name=ref.name,
            commit_id_short=object.short_id,
            commit_dt=datetime.fromtimestamp(object.commit_time),
            commit_author=str(object.author),
            commit=mosaic.put(commit),
            )
        item_list.append(item)
    return item_list


@mark.command(preserve_remote=True)
def ref_log(piece, current_item):
    return htypes.git.log_model(
        repo_name=piece.repo_name,
        repo_dir=piece.repo_dir,
        head_commit=current_item.commit,
        )


@mark.actor.formatter_creg
def format_model(piece):
    return f"Git refs: {piece.repo_name}"
