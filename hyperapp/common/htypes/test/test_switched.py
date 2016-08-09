import unittest
from hyperapp.common.htypes import (
    tString,
    tInt,
    tBool,
    tDateTime,
    Field,
    Interface,
    IfaceRegistry,
    tSwitched,
    TUpdatesRec,
    tIfaceId,
    tPath,
    )
from hyperapp.common.packet_coders import packet_coders


class MetaTypeTest(unittest.TestCase):

    tUpdate = TUpdatesRec(fields=[
        Field('iface', tIfaceId),
        Field('path', tPath),
        Field('diff', tSwitched),
        ])

    iface = Interface('test_iface', diff_type=tString)
    iface_registry = IfaceRegistry(dict(test_iface=iface))
    
    encodings = [
        'json',
        ]
    
    def test_update_instantiate( self ):
        value = self.tUpdate(self.iface, ['test', 'path'], 'the diff')
        self.assertRaises(AssertionError, self.tUpdate, self.iface, ['test', 'path'], 123)

    def test_iface_cmd_switched( self ):
        value = self.tUpdate(self.iface, ['test', 'path'], 'the diff')
        for encoding in self.encodings:
            data = packet_coders.encode(encoding, self.tUpdate, value, self.iface_registry)
            decoded_value = packet_coders.decode(encoding, self.tUpdate, data, self.iface_registry)
            self.assertEqual(value, decoded_value)
