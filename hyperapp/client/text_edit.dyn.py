import logging

from PySide import QtCore, QtGui

from hyperapp.client.module import ClientModule
from . import htypes
from .view import View
from .text_object import TextObject

log = logging.getLogger(__name__)


class TextEditView(View, QtGui.QTextEdit):

    @classmethod
    async def from_state(cls, locale, state, parent, objimpl_registry):
        object = await objimpl_registry.resolve_async(state.object)
        return cls(object, parent)

    @staticmethod
    def get_state_type():
        return this_module.state_type

    def __init__(self, object, parent):
        QtGui.QTextEdit.__init__(self)
        View.__init__(self, parent)
        self.object = object
        self.notify_on_text_changed = True
        self.setPlainText(object.text)
        self.textChanged.connect(self._on_text_changed)
        self.object.subscribe(self)

    def get_state(self):
        return this_module.state_type('text_edit', self.object.get_state())

    def get_title(self):
        return self.object.get_title()

    def get_object(self):
        return self.object

    def get_object_command_list(self, object, kinds=None):
        return object.get_command_list(TextObject.Mode.EDIT, kinds)

    def _on_text_changed(self):
        if self.notify_on_text_changed:
            self.object.text_changed(self.toPlainText(), emitter_view=self)

    # todo: preserve cursor position
    def object_changed(self):
        self.notify_on_text_changed = False
        try:
            self.setPlainText(self.object.text)
        finally:
            self.notify_on_text_changed = True
        View.object_changed(self)

    def __del__(self):
        log.info('~text_edit %r', self)


class ThisModule(ClientModule):

    def __init__(self, module_name, services):
        super().__init__(module_name, services)
        self.state_type = htypes.core.obj_handle
        # services.view_registry.register('text_edit', TextEditView.from_state, services.objimpl_registry)
