import asyncio

from . import htypes
from .code.mark import mark
from .fixtures import feed_fixtures
from .tested.code import sample_tree


@mark.fixture
def model():
    return htypes.sample_tree.model()


def test_sample_tree(model):
    parent = htypes.sample_tree.item(111, "<unused>")
    value = sample_tree.sample_tree(model, parent)
    assert value


async def test_remove_item(feed_factory, model):
    feed = feed_factory(model)
    current_item = htypes.sample_tree.item(111, "<unused>")
    sample_tree.remove_tree_item(model, current_item)
    await feed.wait_for_diffs(count=1)


async def test_append_item(feed_factory, model):
    feed = feed_factory(model)
    current_item = htypes.sample_tree.item(111, "<unused>")
    sample_tree.append_tree_item(model, current_item)
    await feed.wait_for_diffs(count=1)


async def test_insert_item(feed_factory, model):
    feed = feed_factory(model)
    current_item = htypes.sample_tree.item(111, "<unused>")
    sample_tree.insert_tree_item(model, current_item)
    await feed.wait_for_diffs(count=1)


def test_open_sample_fn_tree():
    sample_tree.open_sample_fn_tree()


def test_format(model):
    title = sample_tree.format_model(model)
    assert type(title) is str
