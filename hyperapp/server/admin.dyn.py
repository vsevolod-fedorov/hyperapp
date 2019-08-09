from pony.orm import db_session, commit, Required, Optional, Set, select
from ..common.list_object import ListDiff
from ..common.identity import PublicKey
from ..common.interface import core as core_types
from ..common.interface import admin as admin_iface
from .module import ModuleCommand
from .ponyorm_module import PonyOrmModule
from .object import SmallListObject


class UserList(SmallListObject):

    iface = admin_iface.user_list
    class_name = 'user_list'
    impl_id = 'proxy_list'
    default_sort_column_id = 'id'

    @classmethod
    def resolve(cls, path):
        path.check_empty()
        return cls()

    @classmethod
    def get_path(cls):
        return this_module.make_path(cls.class_name)

    def __init__(self):
        SmallListObject.__init__(self, core_types)

    @db_session
    def fetch_all_elements(self, request):
        return list(map(self.rec2element, this_module.User.select()))

    @classmethod
    def rec2element(cls, rec):
        commands = []
        public_key = PublicKey.from_pem(rec.public_key_pem)
        return cls.Element(cls.Row(rec.id, rec.user_name, public_key.get_short_id_hex()), commands)

    def process_request(self, request):
        if request.command_id == 'add':
            return self.run_command_add(request)
        return SmallListObject.process_request(self, request)

    def run_command_add(self, request):
        public_key = PublicKey.from_der(request.params.public_key_der)
        rec = this_module.User(user_name=request.params.user_name,
                               public_key_pem=public_key.to_pem())
        commit()  # make rec.id
        diff = ListDiff.add_one(self.rec2element(rec))
        subscription.distribute_update(self.iface, self.get_path(), diff)
        return self.ListHandle(self, key=rec.id)


class ThisModule(PonyOrmModule):

    def __init__(self, module_name, services):
        super().__init__(module_name)
        self.User = self.make_entity('User',
                                     user_name=Required(str),
                                     public_key_pem=Required(str),
                                     )

    def resolve(self, iface, path):
        objname = path.pop_str()
        if objname == UserList.class_name:
            return UserList.resolve(path)
        path.raise_not_found()

    def get_commands(self):
        return [
            ModuleCommand('user_list', 'User list', 'Open user list', 'Alt+U', self.name),
            ]

    def run_command(self, request, command_id):
        if command_id == 'user_list':
            return request.make_response_object(UserList())
        return PonyOrmModule.run_command(self, request, command_id)
