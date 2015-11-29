from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


class PublicKey(object):

    @classmethod
    def from_pem( cls, pem ):
        public_key = serialization.load_pem_public_key(public_pem, backend=default_backend())
        return cls('rsa', public_key)

    def __init__( self, algorithm, public_key ):
        assert isinstance(algorithm, basestring), repr(algorithm)
        self.algorithm = algorithm
        self.public_key = public_key

    def to_pem( self ):
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
            )



# Contains assymetryc private key
class Identity(object):

    @classmethod
    def load_from_file( cls, fpath ):
        with open(fpath) as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
        return cls('rsa', private_key)

    def __init__( self, algorithm, private_key ):
        assert isinstance(algorithm, basestring), repr(algorithm)
        assert algorithm == 'rsa', repr(algorithm)  # only algorithm supported for now
        self.algorithm = algorithm
        self.private_key = private_key

    def get_public_key( self ):
        return PublicKey(self.algorithm, self.private_key.public_key())
