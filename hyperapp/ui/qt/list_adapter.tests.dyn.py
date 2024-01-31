import asyncio
from functools import partial

from hyperapp.common.htypes.deduce_value_type import deduce_complex_value_type

from . import htypes
from .services import (
    fn_to_ref,
    mosaic,
    pyobj_creg,
    types,
    )
from .code.context import Context
from .code.list_diff import ListDiffAppend
from .tested.code import list_adapter


def test_static_adapter():
    ctx = Context()
    value = [
        htypes.list_tests.item(1, "First"),
        htypes.list_tests.item(2, "Second"),
        htypes.list_tests.item(3, "Third"),
        ]
    t = deduce_complex_value_type(mosaic, types, value)
    piece = htypes.list_adapter.static_list_adapter(mosaic.put(value, t))
    adapter = list_adapter.StaticListAdapter.from_piece(piece, ctx)
    assert adapter.column_count() == 2
    assert adapter.column_title(0) == 'id'
    assert adapter.column_title(1) == 'title'
    assert adapter.row_count() == 3
    assert adapter.cell_data(1, 0) == 2
    assert adapter.cell_data(2, 1) == "Third"


def sample_list_fn(piece):
    assert isinstance(piece, htypes.list_adapter_tests.sample_list), repr(piece)
    return [
        htypes.list_adapter_tests.item(11, "First item"),
        htypes.list_adapter_tests.item(22, "Second item"),
        htypes.list_adapter_tests.item(33, "Third item"),
        ]


def test_fn_adapter():
    ctx = Context()
    model_piece = htypes.list_adapter_tests.sample_list()
    adapter_piece = htypes.list_adapter.fn_list_adapter(
        model_piece=mosaic.put(model_piece),
        element_t=mosaic.put(pyobj_creg.reverse_resolve(htypes.list_adapter_tests.item)),
        function=fn_to_ref(sample_list_fn),
        want_feed=False,
        )
    adapter = list_adapter.FnListAdapter.from_piece(adapter_piece, ctx)
    assert adapter.column_count() == 2
    assert adapter.column_title(0) == 'id'
    assert adapter.column_title(1) == 'text'
    assert adapter.row_count() == 3
    assert adapter.cell_data(1, 0) == 22
    assert adapter.cell_data(2, 1) == "Third item"


class MockModel:

    def __init__(self, queue):
        self._queue = queue

    def process_diff(self, diff):
        self._queue.put_nowait(diff)


def _send_diff(feed):
    item = htypes.sample_list.item(44, "Sample item #4")
    feed.send(ListDiffAppend(item))


def feed_sample_list_fn(piece, feed):
    assert isinstance(piece, htypes.list_adapter_tests.sample_list), repr(piece)
    loop = asyncio.get_running_loop()
    loop.call_soon(partial(_send_diff, feed))
    return [
        htypes.list_adapter_tests.item(11, "First item"),
        htypes.list_adapter_tests.item(22, "Second item"),
        htypes.list_adapter_tests.item(33, "Third item"),
        ]


async def test_feed_fn_adapter():
    ctx = Context()
    model_piece = htypes.list_adapter_tests.sample_list()
    adapter_piece = htypes.list_adapter.fn_list_adapter(
        model_piece=mosaic.put(model_piece),
        element_t=mosaic.put(pyobj_creg.reverse_resolve(htypes.list_adapter_tests.item)),
        function=fn_to_ref(feed_sample_list_fn),
        want_feed=True,
        )

    adapter = list_adapter.FnListAdapter.from_piece(adapter_piece, ctx)
    queue = asyncio.Queue()
    model = MockModel(queue)
    adapter.subscribe(model)

    assert adapter.column_count() == 2
    assert adapter.column_title(0) == 'id'
    assert adapter.column_title(1) == 'text'
    assert adapter.row_count() == 3
    assert adapter.cell_data(1, 0) == 22
    assert adapter.cell_data(2, 1) == "Third item"

    diff = await queue.get()
    assert isinstance(diff, ListDiffAppend), repr(diff)
    assert diff.item.id == 44
