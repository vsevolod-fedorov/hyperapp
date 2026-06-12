from .htypes.packet_coders import packet_coders
from .cdr_encoder import CdrEncoder
from .cdr_decoder import CdrDecoder
from .dict_encoder import JsonEncoder, YamlEncoder
from .dict_decoder import JsonDecoder, YamlDecoder


def register_coders():
    packet_coders.register('cdr', CdrEncoder, CdrDecoder)
    packet_coders.register('json', JsonEncoder, JsonDecoder)
    packet_coders.register('yaml', YamlEncoder, YamlDecoder)
