from .dict_encoders import JsonEncoder, YamlEncoder
from .dict_decoders import JsonDecoder, YamlDecoder
from .cdr_encoder import CdrEncoder
from .cdr_decoder import CdrDecoder

    
class Coders(object):

    def __init__( self, encoder, decoder ):
        self.encoder = encoder
        self.decoder = decoder


class PacketCoders(object):

    def __init__( self ):
        self._coders = {}  # encoding -> Coders

    def register( self, encoding, encoder, decoder ):
        assert isinstance(encoding, str), repr(encoding)
        self._coders[encoding] = Coders(encoder, decoder)

    def resolve( self, encoding ):
        assert encoding in self._coders, repr(encoding)  # Unknown encoding
        return self._coders[encoding]

    def decode( self, encoding, t, data, iface_registry=None ):
        coders = self.resolve(encoding)
        return coders.decoder(iface_registry).decode(t, data)

    def encode( self, encoding, t, object, iface_registry=None ):
        coders = self.resolve(encoding)
        return coders.encoder(iface_registry).encode(t, object)


packet_coders = PacketCoders()
packet_coders.register('json', lambda iface_registry: JsonEncoder(iface_registry, pretty=False), JsonDecoder)
packet_coders.register('json_pretty', lambda iface_registry: JsonEncoder(iface_registry, pretty=True), JsonDecoder)
packet_coders.register('yaml', YamlEncoder, YamlDecoder)
packet_coders.register('cdr', CdrEncoder, CdrDecoder)
