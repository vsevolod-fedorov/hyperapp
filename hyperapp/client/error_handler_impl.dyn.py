from ..common.htypes import Field
from ..common.interface import error as error_types
from ..common.interface import core as core_types
from ..common.interface import text_object as text_object_types
from .module import ClientModule
from .error_handler_hook import set_error_handler


MODULE_NAME = 'ereror_handler_impl'

ERROR_HANDLER_VIEW_ID = 'error_handler'
ERROR_HANDLER_CLASS_ID = 'error_handler'


def register_views(registry, services):
    registry.register(ERROR_HANDLER_VIEW_ID, this_module.resolve_error_handler)


class ThisModule(ClientModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME, services)
        self._resources_manager = services.resources_manager
        self._error_handle_t = services.types.core.handle.register(
            ERROR_HANDLER_CLASS_ID, base=services.types.core.view_handle, fields=[
                Field('error', error_types.error),
                ])
        set_error_handler(self.error_handler)

    async def resolve_error_handler(self, locale, state, parent):
        resource_id = ['error_message', state.error._class_id, locale]
        error_message_resource = self._resources_manager.resolve(resource_id)
        if error_message_resource:
            message = error_message_resource.message.format(error=state.error)
        else:
            message = 'Unexpected error: %s' % state.error._class_id
        # somehow this state got stuck forever, holding all objects in it's traceback, including views subscribed to events
        state.error.__traceback__ = None
        obj = text_object_types.text_object('text', message)
        return core_types.obj_handle('text_view', obj)

    def error_handler(self, exception):
        if not isinstance(exception, error_types.error):
            exception = error_types.unknown_client_error()
        # using intermediate handle is the simplest way to get current locale
        return self._error_handle_t(ERROR_HANDLER_VIEW_ID, exception)
