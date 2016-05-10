import os.path
from ..common.htypes import iface_registry
from .proxy_registry import proxy_class_registry
from .proxy_list_object import ProxyListObject


class RefList(ProxyListObject):

    @staticmethod
    def get_objimpl_id():
        return 'ref_list'

    def get_module_ids( self ):
        return [this_module_id]

    def run_command( self, command_id, initiator_view=None, **kw ):
        if command_id == 'add':
            return self.run_command_add(initiator_view)
        return ProxyListObject.run_command(self, command_id, initiator_view, **kw)

    def run_command_add( self, initiator_view ):
        self.execute_request('add', initiator_view, target_url=self.get_default_url().to_data())

    # todo
    def get_default_url( self ):
        iface = iface_registry.resolve('fs_dir')
        return self.server.make_url(iface, ['file', os.path.expanduser('~')])


proxy_class_registry.register(RefList)
