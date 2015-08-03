from . interface import TObject
from .mapper import Mapper


class ObjectResolver(Mapper):

    def __init__( self, peer, resolver ):
        self.peer = peer
        self.resolver = resolver  # obj info -> handle

    dispatch = Mapper.dispatch

    @dispatch.register(TObject)
    def decode_object( self, t, value, path ):
        objinfo = self.decode_record(t, value, path)
        return self.resolver(self.peer, objinfo)
