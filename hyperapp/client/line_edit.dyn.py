# line edit component / widget

import logging
from enum import Enum
from PySide2 import QtCore, QtWidgets

from hyperapp.client.object import Object
from hyperapp.client.module import ClientModule

from . import htypes
from .layout import RootVisualItem, Layout
from .view import View

log = logging.getLogger(__name__)


class LineObject(Object):

    category_list = ['line']

    @classmethod
    def from_state(cls, state):
        return cls(state.line)

    def __init__(self, line):
        self._line = line
        super().__init__()

    def get_title(self):
        return 'Line'

    @property
    def data(self):
        return htypes.line.line(self.line)

    def get_value(self):
        return self._line

    @property
    def line(self):
        return self._line

    @line.setter
    def line(self, line):
        self._line = line
        self._notify_object_changed()

    def line_changed(self, new_line, emitter_view=None):
        log.debug('line_object.line_changed: %r', new_line)
        self._line = new_line
        self._notify_object_changed(emitter_view)

    def __del__(self):
        log.info('~line_object %r', self)


class LineEditView(View, QtWidgets.QLineEdit):

    impl_id = 'line_edit'

    class Mode(Enum):
        VIEW = 'view'
        EDIT = 'edit'

    def __init__(self, object, mode):
        QtWidgets.QLineEdit.__init__(self, object.line)
        View.__init__(self)
        self._object = object
        self._mode = mode
        self._notify_on_line_changed = True
        self.setReadOnly(self._mode == self.Mode.VIEW)
        self.textChanged.connect(self._on_line_changed)
        self._object.subscribe(self)

    def _on_line_changed(self, line):
        log.debug('line_edit.on_line_changed: %r', line)
        if self._notify_on_line_changed:
            self._object.line_changed(line, emitter_view=self)

    # todo: preserve cursor position
    def object_changed(self):
        self._notify_on_line_changed = False
        try:
            self.setText(self._object.line)
        finally:
            self._notify_on_line_changed = True
        View.object_changed(self)

    def __del__(self):
        log.info('~line_edit')


class LineEditLayout(Layout):

    def __init__(self, object, path, command_hub, piece_opener, mode):
        super().__init__(path)
        self._object = object
        self._mode = mode

    def get_view_ref(self):
        assert 0  # todo

    async def create_view(self):
        return LineEditView(self._object, self._mode)

    async def visual_item(self):
        return RootVisualItem('LineEdit')


class ThisModule(ClientModule):

    def __init__(self, module_name, services):
        super().__init__(module_name, services)
        services.object_registry.register_type(htypes.line.line, LineObject.from_state)
        services.default_object_layouts.register('line', LineObject.category_list, self._make_line_layout_rec)
        services.available_object_layouts.register('line', LineObject.category_list, self._make_line_layout_rec)
        services.object_layout_registry.register_type(htypes.line.line_edit_layout, self._produce_line_layout)

    async def _make_line_layout_rec(self, object):
        return htypes.line.line_edit_layout()

    async def _produce_line_layout(self, state, object, command_hub, piece_opener):
        return LineEditLayout(object, [], command_hub, piece_opener, LineEditView.Mode.VIEW)
