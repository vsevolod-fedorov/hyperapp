import codecs

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

from .htypes import ref_t, capsule_t, bundle_t
from .htypes.packet_coders import packet_coders


DEFAULT_HASH_ALGORITHM = 'sha512'
MAX_REF_REPR_LEN = 60
BUNDLE_ENCODING = 'json'

# special case indicating packets must be sent to the peer from which this route is received
LOCAL_TRANSPORT_REF = ref_t('', b'LOCAL_TRANSPORT')


def ref_repr(ref):
    if ref == LOCAL_TRANSPORT_REF:
        return ref.hash.decode()
    else:
        hash_hex = codecs.encode(ref.hash[:4], 'hex').decode()
        return '%s:%s' % (ref.hash_algorithm, hash_hex)

def ref_list_repr(ref_list):
    ref_list = list(ref_list)  # add iterable support
    if not ref_list:
        return 'none'
    return ', '.join(map(ref_repr, ref_list))

def make_ref(capsule):
    assert isinstance(capsule, capsule_t)
    # use same encoding for capsule as for object
    encoded_capsule = packet_coders.encode(capsule.encoding, capsule)
    digest = hashes.Hash(hashes.SHA512(), backend=default_backend())
    digest.update(encoded_capsule)
    hash = digest.finalize()
    return ref_t(DEFAULT_HASH_ALGORITHM, hash)

def make_object_ref(object, t):
    capsule = make_capsule(object, t)
    return make_ref(capsule)

def encode_bundle(bundle):
    return packet_coders.encode(BUNDLE_ENCODING, bundle)

def decode_bundle(encoded_bundle):
    return packet_coders.decode(BUNDLE_ENCODING, encoded_bundle, bundle_t)
