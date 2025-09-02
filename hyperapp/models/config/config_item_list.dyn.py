from collections import defaultdict

from hyperapp.boot.htypes import Type

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.data_browser import data_browser


@mark.model(key='key')
def config_item_list(piece, system, format):

    def enum_items(config):
        if type(config) in {list, set}:
            for item in config:
                yield ('', item)
        elif type(config) is dict:
            for key, value in config.items():
                for _, item in enum_items(value):
                    yield key, item
        else:
            yield ('', config)

    key_to_item_layer = defaultdict(list)
    for layer_name, layer in system.name_to_layer.items():
        try:
            config = layer.config[piece.service_name]
        except KeyError:
            continue
        for key, value in enum_items(config):
            key_to_item_layer[key].append((value, layer_name))

    def item_layers(key, value):
        result = []
        for v, layer_name in key_to_item_layer.get(key, []):
            if v is value:
                result.append(layer_name)
        return result

    config = system.get_config_template(piece.service_name)
    item_list = []
    for key, value in sorted(enum_items(config), key=lambda rec: str(rec[0])):
        if isinstance(key, Type):
            key_data = pyobj_creg.actor_to_piece(key)
        else:
            key_data = key
        layers = item_layers(key, value)
        item = htypes.config_item_list.item(
            key=mosaic.put(key_data),
            key_str=format(key),
            value_str=str(value),
            layers=tuple(layers),
            layers_str=", ".join(layers),
            )
        item_list.append(item)
    return item_list


@mark.command
def open_config_item_list(piece, current_item):
    return htypes.config_item_list.model(current_item.service_name)


@mark.command
def open_config_key(piece, current_item):
    key = web.summon(current_item.key)
    return data_browser(key)


@mark.crud.get_layer(commit_action='move')
def config_item_get_layer(piece, layers):
    if not layers:
        return None
    return htypes.config_layer_list.layer(
        name=layers[0],
        )


@mark.crud.move
def config_item_move_to_another_layer(piece, key, layers, value, system):
    source_layer_name = layers[0]
    target_layer_name = value.name
    if target_layer_name == source_layer_name:
        return
    source_layer = system.name_to_layer[source_layer_name]
    target_layer = system.name_to_layer[target_layer_name]
    key_piece = web.summon(key)
    service_config = system.get_config_template(piece.service_name)
    value_template = service_config[key_piece]
    target_layer.set(piece.service_name, key_piece, value_template)
    source_layer.remove(piece.service_name, key_piece)
    return (piece, key)


@mark.command.remove
def remove(piece, current_item, system):
    layer_name = current_item.layers[0]  # Will remove from first layer.
    layer = system.name_to_layer[layer_name]
    key = web.summon(current_item.key)
    layer.remove(piece.service_name, key)
    return True


@mark.actor.formatter_creg
def format_model(piece):
    return f"Config for service: {piece.service_name}"
