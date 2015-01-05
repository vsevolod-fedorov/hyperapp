import os.path
from pony.orm import *
from module import Module


SQLITE_DB_PATH = os.path.expanduser('~/.hyperapp-server-db.sqlite')
MODULE_NAME = 'ponyorm'


# base class for modules using ponyorm
class PonyOrmModule(Module):

    def __init__( self, name ):
        Module.__init__(self, name)
        self.db = module.db

    def make_entity( self, name, **fields ):
        return self.make_inherited_entity(name, self.db.Entity, **fields)

    def make_inherited_entity( self, name, base, **fields ):
        return type(name, (base,), fields)


class ThisModule(Module):

    def __init__( self ):
        Module.__init__(self, MODULE_NAME)
        #sql_debug(True)
        self.db = Database('sqlite', SQLITE_DB_PATH, create_db=True)

    def init_phase2( self ):
        self.db.generate_mapping(create_tables=True)


module = ThisModule()
