import logging
from datetime import datetime

import pygit2

from . import htypes
from .services import (
    mosaic,
    )
from .code.mark import mark

log = logging.getLogger(__name__)


def load_commit(id_to_commit, root):
    log.info("Loading commits for: %s", root.id)
    unloaded = {root}
    while unloaded:
        git_commit = unloaded.pop()
        if git_commit.id in id_to_commit:
            continue
        parents = []
        for git_parent in git_commit.parents:
            try:
                parent_commit = id_to_commit[git_parent.id]
            except KeyError:
                unloaded.add(git_parent)
            else:
                parents.append(parent_commit)
        if len(parents) != len(git_commit.parents):
            unloaded.add(git_commit)
            continue
        commit = htypes.git.commit(
            parents=tuple(mosaic.put(p) for p in parents),
            time=datetime.fromtimestamp(git_commit.commit_time),
            author=str(git_commit.author),
            committer=str(git_commit.committer),
            message=git_commit.message,
            )
        id_to_commit[git_commit.id] = commit
    log.info("Loaded %d commits", len(id_to_commit))
    return id_to_commit[root.id]


@mark.model
def ref_list(piece):
    repo = pygit2.Repository(piece.repo_dir)
    id_to_commit = {}
    item_list = []
    for ref_name in repo.references:
        ref = repo.references[ref_name].resolve()
        object = repo[ref.target]
        commit = load_commit(id_to_commit, object)
        item = htypes.git.ref_item(
            name=ref_name,
            commit_id_short=object.short_id,
            commit_author=str(object.author),
            commit_dt=datetime.fromtimestamp(object.commit_time),
            commit=mosaic.put(commit),
            )
        item_list.append(item)
    return item_list
