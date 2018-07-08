import os.path

from ..common.interface import hyper_ref as href_types
from ..common.local_server_paths import LOCAL_SERVER_DYNAMIC_REF_LIST_REF_PATH, load_bundle_from_file
from .command import command
from .module import ClientModule


MODULE_NAME = 'local_server_ref_list'


class ThisModule(ClientModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME, services)
        self._handle_resolver = services.handle_resolver
        self._local_server_ref = self._load_local_server_ref(services.ref_registry)

    @command('open_local_server')
    async def open_local_server(self):
        return (await self._handle_resolver.resolve(self._local_server_ref))

    def _load_local_server_ref(self, ref_registry):
        bundle = load_bundle_from_file(LOCAL_SERVER_DYNAMIC_REF_LIST_REF_PATH)
        ref_registry.register_bundle(bundle)
        assert len(bundle.roots) == 1
        return bundle.roots[0]
