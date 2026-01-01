from . import htypes
from .code.mark import mark
from .tested.code import config_layer_list


@mark.fixture
def model():
    return htypes.config_layer_list.model()


def test_layer_list_model(model):
    item_list = config_layer_list.config_layer_list(model)
    assert item_list
    assert isinstance(item_list[0], htypes.config_layer_list.item)


def test_open_service_list(system, model):
    current_key = system.default_layer_name
    model = config_layer_list.open_service_list(model, current_key)
    assert isinstance(model, htypes.config_service_list.model)


def test_open():
    model = config_layer_list.open_config_layer_list()
    assert isinstance(model, htypes.config_layer_list.model)


def test_selector_get():
    # value is actually unused.
    value = htypes.config_layer_list.layer(
        name='sample-layer',
        )
    piece, key = config_layer_list.layer_get(value)
    assert isinstance(piece, htypes.config_layer_list.model)
    assert type(key) is str


def test_selector_pick():
    model = htypes.config_layer_list.model()  # Unused.
    current_item = htypes.config_layer_list.item(
        name='sample-layer',
        service_count=0,  # Unused.
        )
    value = config_layer_list.layer_pick(model, current_item)
    assert value == htypes.config_layer_list.layer('sample-layer')


def test_format_model(model):
    title = config_layer_list.format_model(model)
    assert type(title) is str
