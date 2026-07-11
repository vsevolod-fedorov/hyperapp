import pytest

from hyperapp.boot.htypes import tString, tInt, TList, TRecord
from hyperapp.boot.htypes.packet_coders import packet_coders
from hyperapp.boot.dict_decoder import NamedPairsDictDecoder
from hyperapp.boot.dict_encoder import NamedPairsDictEncoder


def test_named_pair():
    encoder = NamedPairsDictEncoder()
    decoder = NamedPairsDictDecoder()
    value_t = TRecord('sample', 'value', {
        'an_int': tInt,
        })
    field_t = TRecord('sample', 'field', {
        'key': tString,
        'value': value_t,
        })
    t = TRecord('sample', 'root', {
        'fields': TList(field_t),
        })
    data = {
        'fields': {
            'first': {
                'an_int': 111,
                },
            'second': {
                'an_int': 222,
                },
            },
        }
    value = decoder.decode_dict(t, data)
    decoded_data = encoder.encode(value, t)
    assert decoded_data == data
