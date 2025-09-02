import asyncio
import inspect
import logging
import weakref

from . import htypes
from .services import (
    deduce_t,
    )
from .code.mark import mark
from .code.list_diff import IndexListDiff, KeyListDiff
from .code.tree_diff import TreeDiff
from .code.value_diff import SetValueDiff
from .code.feed_ctr import ListFeedCtr, IndexTreeFeedCtr, ValueFeedCtr

log = logging.getLogger(__name__)


class FeedDiscoverer:

    def __init__(self, ctr_collector, piece_t):
        self._ctr_collector = ctr_collector
        self._piece_t = piece_t
        self.ctr = None
        self._constructor_added = False
        self._subscribers = weakref.WeakSet()
        self._got_diff = asyncio.Condition()
        self._got_diff_count = 0

    def subscribe(self, subscriber):
        self._subscribers.add(subscriber)

    def send(self, diff):
        log.info("Feed discoverer: send: %s", diff)
        frame = inspect.stack()[1].frame
        python_module_name = frame.f_globals['__name__']
        module_action = self._ctr_collector.get_module_action(python_module_name)
        assert module_action is not self._ctr_collector.Action.NotSet
        if module_action is not self._ctr_collector.Action.Ignore:
            self._deduce_and_store_ctr(module_action.module_name, diff)
            if self.ctr and not self._constructor_added:
                self._add_constructor()
        for subscriber in self._subscribers:
            subscriber.process_diff(diff)

    async def wait_for_diffs(self, count, timeout=5):
        async with self._got_diff:
            while self._got_diff_count < count:
                async with asyncio.timeout(5):
                    await self._got_diff.wait()

    def _deduce_and_store_ctr(self, module_name, diff):
        if isinstance(diff, (
                IndexListDiff.Insert,
                IndexListDiff.Append,
                IndexListDiff.Replace,
                KeyListDiff.Insert,
                KeyListDiff.Append,
                KeyListDiff.Replace,
                )):
            item_t = deduce_t(diff.item)
            ctr = ListFeedCtr(
                module_name=module_name,
                model_t=self._piece_t,
                item_t=item_t,
                )
            if self.ctr:
                if ctr != self.ctr:
                    raise RuntimeError(f"Attempt to send different diff types to a feed: {self.ctr} and {ctr}")
            else:
                self.ctr = ctr
                log.info("Feed: Deduced feed type: %s [%s]", self.ctr, item_t)
        elif isinstance(diff, (IndexListDiff.Remove, KeyListDiff.Remove)):
            ctr = ListFeedCtr(
                module_name=module_name,
                model_t=self._piece_t,
                item_t=None,
                )
            if self.ctr and not self.ctr.item_t:
                if ctr != self.ctr:
                    raise RuntimeError(f"Attempt to send different diff types to a feed: {self.ctr} and {ctr}")
            elif not self.ctr:
                self.ctr = ctr
                log.info("Feed: Unknown item type for: %s", self.ctr)
        elif self.ctr and isinstance(diff, (
                IndexListDiff.Remove,
                IndexListDiff.Modify,
                KeyListDiff.Remove,
                KeyListDiff.Modify,
                )):
            if not isinstance(self.ctr, htypes.feed.list_feed_ctr):
                raise RuntimeError(f"Attempt to send different diff types to a feed: {self.ctr} and list diff ({diff})")
        elif isinstance(diff, (
                TreeDiff.Insert,
                TreeDiff.Append,
                TreeDiff.Replace,
                )):
            item_t = deduce_t(diff.item)
            ctr = IndexTreeFeedCtr(
                module_name=module_name,
                model_t=self._piece_t,
                item_t=item_t,
                )
            if self.ctr:
                if ctr != self.ctr:
                    raise RuntimeError(f"Attempt to send different diff types to a feed: {self.ctr} and {feed}")
            else:
                self.ctr = ctr
                log.info("Feed: Deduced feed type: %s [%s]", self.ctr, item_t)
        elif isinstance(diff, TreeDiff.Remove):
            ctr = IndexTreeFeedCtr(
                module_name=module_name,
                model_t=self._piece_t,
                item_t=None,
                )
            if self.ctr:
                if ctr != self.ctr:
                    raise RuntimeError(f"Attempt to send different diff types to a feed: {self.ctr} and {feed}")
            else:
                self.ctr = ctr
                log.info("Feed: Unknown item type: %s", self.ctr)
        elif self.ctr and isinstance(diff, (
                TreeDiff.Remove,
                TreeDiff.Modify,
                )):
            if not isinstance(self.ctr, htypes.feed.index_tree_feed_ctr):
                raise RuntimeError(f"Attempt to send different diff types to a feed: {self.ctr} and tree diff ({diff})")
        elif isinstance(diff, SetValueDiff):
            value_t = deduce_t(diff.new_value)
            ctr = ValueFeedCtr(
                module_name=module_name,
                model_t=self._piece_t,
                value_t=value_t,
                )
            if self.ctr:
                if ctr != self.ctr:
                    raise RuntimeError(f"Attempt to send different diff types to a feed: {self.ctr} and {feed}")
            else:
                self.ctr = ctr
                log.info("Feed: Deduced feed type: %s [%s]", self.ctr, value_t)
        else:
            raise NotImplementedError(f"Not implemented: feed detection for diff: {diff}")
        loop = asyncio.get_running_loop()  # Tests with diffs expected to be async.
        loop.call_soon(asyncio.create_task, self._notify_new_diff())

    async def _notify_new_diff(self):
        async with self._got_diff:
            self._got_diff_count += 1
            self._got_diff.notify_all()

    def _add_constructor(self):
        self._ctr_collector.add_constructor(self.ctr)
        self._constructor_added = True


@mark.fixture
def feed_factory_fixture_cache():
    return {}


@mark.fixture
def feed_factory(config, ctr_collector, feed_factory_fixture_cache, piece):
    log.info("Discovered feed piece: %s", piece)
    try:
        return feed_factory_fixture_cache[piece]
    except KeyError:
        pass
    piece_t = deduce_t(piece)
    feed = FeedDiscoverer(ctr_collector, piece_t)
    feed_factory_fixture_cache[piece] = feed
    return feed
