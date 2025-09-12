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


def _commit_to_item(commit):
    return htypes.git.log_item(
        id_short=commit.short_id,
        dt=commit.time,
        author=commit.author,
        message=commit.message,
        )


def _send_diff(feed, commit):
    item = _commit_to_item(commit)
    diff = IndexListDiff.Append(item)
    feed.send(diff)



@mark.service
def _git_log_thread_pool():
    pool = ThreadPoolExecutor(max_workers=1)
    log.info("Sample list: Thread pool created")
    yield pool
    pool.shutdown()


def _load_commits(feed, head_commit, git_log, scheduler=None):
    if git_log.commit_list:
        last_commit = git_log.commit_list[-1]
    else:
        git_log.commit_list.append(head_commit)
        _send_diff(feed, head_commit)
        last_commit = head_commit
    count = 0
    while last_commit.parents:
        # We do not need proper log history, just enough items to show.
        # So, just taking first parent every time.
        last_commit = web.summon(last_commit.parents[0])
        git_log.commit_list.append(last_commit)
        _send_diff(feed, last_commit)
        count += 1
        if scheduler and count >= 10:
            scheduler()
            return


def _schedule_async(loop, feed, head_commit, git_log):
    scheduler = partial(_schedule_async, loop, feed, head_commit, git_log)
    loop.call_soon(_load_commits, feed, head_commit, git_log, scheduler)


def _schedule_log_loading(thread_pool, feed, head_commit, git_log):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        log.info("Git log: Loading Synchronously")
        thread_pool.submit(_load_commits, feed, head_commit, git_log)
    else:
        log.info("Git log: Loading Asynchronously")
        _schedule_async(loop, feed, head_commit, git_log)


@mark.model
def log_model(piece, repo_list, _git_log_thread_pool, feed_factory):
    repo = repo_list.repo_by_dir(piece.repo_dir)
    head_commit = web.summon(piece.head_commit)
    git_log = repo.head_log(head_commit)
    item_list = [_commit_to_item(commit) for commit in git_log.commit_list]
    if not git_log.feed_is_running:
        feed = feed_factory(piece)
        _schedule_log_loading(_git_log_thread_pool, feed, head_commit, git_log)
        git_log.feed_is_running = True
    return item_list


@mark.actor.formatter_creg
def format_model(piece):
    return f"Git commits: {piece.repo_name}"
