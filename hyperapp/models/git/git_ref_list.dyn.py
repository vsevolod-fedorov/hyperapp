from datetime import datetime

import pygit2

from . import htypes
from .code.mark import mark


@mark.model
def ref_list(piece):
    repo = pygit2.Repository(piece.repo_dir)
    item_list = []
    for ref_name in repo.references:
        ref = repo.references[ref_name].resolve()
        object = repo[ref.target]
        item = htypes.git.ref_item(
            name=ref_name,
            commit_id_short=object.short_id,
            commit_author=str(object.author),
            commit_dt=datetime.fromtimestamp(object.commit_time),
            )
        item_list.append(item)
    return item_list
