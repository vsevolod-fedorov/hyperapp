from . import htypes
from .services import (
    pyobj_creg,
    )
from .code.mark import mark
from .code.context import Context
from .tested.code import model_list


@mark.fixture
def model():
    return htypes.model_list.model()


def test_model(model):
    item_list = model_list.model_list_model(model)
    assert type(item_list) is list


def test_open():
    model = model_list.open_model_list()
    assert model


def test_format_model(model):
    title = model_list.format_model(model)
    assert type(title) is str


def test_format_model_arg():
    value = htypes.model_list.model_arg(
        model_t=pyobj_creg.actor_to_ref(htypes.builtin.string),
        )
    title = model_list.format_model_arg(value)
    assert type(title) is str


def test_selector_open():
    ctx = Context(
        value=htypes.model_list.model_arg(
            model_t=pyobj_creg.actor_to_ref(htypes.builtin.string),
            ),
        )
    model = model_list.model_list_open(ctx)
    assert model


def test_selector_pick(model):
    ctx = Context(
        model=model,
        current_item=htypes.model_list.item(
            model_t=pyobj_creg.actor_to_ref(htypes.builtin.string),
            model_t_name="<unused>",
            ui_t="<unused>",
            fn="<unused>",
            ),
        )
    value = model_list.model_list_pick(ctx)
    assert value == htypes.model_list.model_arg(
        model_t=pyobj_creg.actor_to_ref(htypes.builtin.string),
        )
