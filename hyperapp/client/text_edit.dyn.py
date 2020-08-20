import logging

from PySide2 import QtCore, QtWidgets

from hyperapp.client.object import ObjectObserver
from hyperapp.client.module import ClientModule
from . import htypes
from .text_object import TextObject

_log = logging.getLogger(__name__)


class TextEditView(QtWidgets.QTextEdit, ObjectObserver):

    def __init__(self, object):
        super().__init__()
        self.object = object
        self.notify_on_text_changed = True
        self.setPlainText(object.text)
        self.textChanged.connect(self._on_text_changed)
        self.object.subscribe(self)

    def get_title(self):
        return self.object.get_title()

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
        _log.info('~text_edit %r', self)


class ThisModule(ClientModule):

    def __init__(self, module_name, services):
        super().__init__(module_name, services)
