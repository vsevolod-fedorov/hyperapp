import os.path
from pathlib import Path

from ..common.htypes.packet_coders import packet_coders
from ..common.ref import phony_ref
from ..common.services import Services
from ..common.module import ModuleRegistry
from .cache_repository import CacheRepository


CACHE_DIR = os.path.expanduser('~/.cache/hyperapp/client')
CACHE_CONTENTS_ENCODING = 'json'
CACHE_FILE_EXT = '.json'
TYPE_MODULE_EXT = '.types'


type_module_list = [
    'resource',
    'fs',
    'layout',
    'tab_view',
    'navigator',
    'menu_bar',
    'command_pane',
    'window',
    'root_layout',
    'application_state',
    'object_type',
    'object_layout_association',
    'text',
    'list_object',
    'tree_object',
    'record_object',
    'code_command_chooser',
    'command_list',
    'layout_editor',
    'record_view',
    'line',
    'master_details',
    'list_view',
    'tree_view',
    'tree_to_list_adapter',
    'data_viewer',
    'log_viewer',
    'params_editor',
    'list_view_sample',
    'tree_view_sample',
    'view_chooser',
    'params_editor_sample',
    ]

code_module_list = [
    'common.dict_coders',
    'common.visitor',
    'common.ref_collector',
    'common.unbundler',
    'common.resource_registry',
    'common.resource_resolver',
    'common.resource_loader',
    'common.fs_service_impl',
    'client.module_command_registry',
    'client.async_web',
    'client.code_registry',
    'client.objimpl_registry',
    'client.object_registry',
    'client.view',
    'client.composite',
    'client.column',
    'client.list_object',
    'client.tree_object',
    'client.simple_list_object',
    # 'client.splitter',
    'client.command_hub',
    'client.view_registry',
    'client.object_layout_association',
    'client.items_view',
    'client.layout_handle',
    'client.layout_command',
    'client.self_command',
    'client.layout',
    'client.record_object',
    'client.chooser',
    'client.params_editor',
    'client.object_command',
    'client.params_editor_object',
    'client.view_chooser',
    'client.default_state_builder',
    'client.layout_manager',
    'client.code_command_chooser',
    'client.command_list',
    'client.layout_editor',
    'client.tab_view',
    'client.menu_bar',
    'client.command_pane',
    'client.window',
    # 'client.navigator.history_list',
    'client.navigator.navigator',
    'client.record_view',
    # 'client.navigator.module',
    # 'client.form',
    # 'code_repository',
    # 'identity',
    # 'redirect_handle',
    # 'form_view',
    # 'client.error_handler_impl',
    # 'bookmarks',
    # 'client.ref_redirect_handle',
    # 'client.line_list_panel',
    # 'client.narrower',
    # 'client.url_clipboard',
    'client.text_object',
    'client.data_viewer',
    'client.log_viewer',
    'client.application_state_storage',
    'client.master_details',
    'client.line_edit',
    'client.text_view',
    'client.list_view',
    'client.list_view_sample',
    'client.tree_view',
    'client.tree_view_sample',
    'client.tree_to_list_adapter',
    'client.tree_to_list_adapter_sample',
    'client.params_editor_sample',
    'client.fs',
    'client.fs_local_service',
    'client.fs_remote_service',
    'client.ref_list',
    'client.local_server_ref_list',
    'client.wiki_text_sample',
    'client.blog',
    ]


class ClientServicesBase(Services):

    def __init__(self, event_loop):
        super().__init__()
        self.event_loop = event_loop


class ClientServices(ClientServicesBase):

    def __init__(self, event_loop):
        super().__init__(event_loop)
        self._hyperapp_client_dir = self.hyperapp_dir / 'client'
        self.client_resources_dir = self._hyperapp_client_dir
        self.init_services()
        self.client_module_dir = self._hyperapp_client_dir
        self.init_modules(type_module_list, code_module_list)
        # enable application resources to work; todo: move application commands to dynamic module
        self.local_code_module_registry.register('client.application', phony_ref('application'))

    async def async_init(self):
        for method in self.module_registry.enum_modules_method('async_init'):
            await method(self)
