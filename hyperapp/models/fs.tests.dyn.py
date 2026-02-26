from . import htypes
from .code.mark import mark
from .code.context import Context
from .tested.code import fs


@mark.fixture
def model():
    return htypes.fs.model()


def test_open_fs():
    model = fs.open_fs()
    assert isinstance(model, htypes.fs.model)


def test_model(model):
    parent = htypes.fs.item(
        name='<unused>',
        size=None,
        )
    path = ['etc']
    item_list = fs.fs_model(model, path)
    assert type(item_list) is list
    assert item_list
    assert isinstance(item_list[0], htypes.fs.item)


def test_formatter(model):
    title = fs.format_model(model)
    assert type(title) is str


def test_selector_open(model):
    ctx = Context(
        value=htypes.fs.path(
            parts=('tmp', 'sample'),
            ),
        )
    model, current_path = fs.fs_open(ctx)
    assert model == model
    assert current_path == ('tmp', 'sample')


def test_selector_pick(model):
    ctx = Context(
        model=model,
        current_path=('tmp', 'sample'),
        )
    value = fs.fs_pick(ctx)
    assert value == htypes.fs.path(
        parts=('tmp', 'sample'),
        )
