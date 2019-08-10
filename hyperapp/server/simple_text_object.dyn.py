# test for returning non-proxy object to client, text object

import os.path
from .. common.interface import core as core_types
from .. common.interface import text as text_object_types
from .module import Module, ModuleCommand


sample_text = '''
Lorem Ipsum is simply dummy text of the printing and typesetting industry.
Lorem Ipsum has been the industry's standard dummy text ever since the 1500s,
when an unknown printer took a galley of type and scrambled it to make a type specimen book.
It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged.
It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages,
and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.
'''


class ThisModule(Module):

    def __init__(self, module_name, services):
        super().__init__(module_name)

    def get_commands(self):
        return [
            ModuleCommand('get_text_obj', 'Get text', 'Produce test text object', None, self.name),
            ModuleCommand('get_test_text_obj', 'Get test text', 'Produce test text object', None, self.name),
            ]

    def run_command(self, request, command_id):
        if command_id == 'get_text_obj':
            object = text_object_types.text_object('text', sample_text)
            handle = core_types.obj_handle('text_view', object)
            return request.make_response_handle(handle)
        if command_id == 'get_test_text_obj':
            object = text_object_types.text_object('test_text', sample_text)
            handle = core_types.obj_handle('text_view', object)
            return request.make_response_handle(handle)
        return Module.run_command(self, request, command_id)
