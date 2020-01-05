from collections import OrderedDict

from hyperapp.client.module import ClientModule

from . import htypes


class ParamsEditor:
    pass


class ThisModule(ClientModule):

    def __init__(self, module_name, services):
        super().__init__(module_name, services)
        self._ref_registry = services.ref_registry
        services.params_editor = self._open_params_editor

    def _open_params_editor(self, piece, command, args, kw):
        bound_arguments = command.bound_arguments(*args, **kw)
        wanted_arguments = [
            (name, p.annotation) for name, p in bound_arguments.signature.parameters.items()
            if name not in bound_arguments.arguments
            ]
        fields = [
            htypes.params_editor.field(name, self._ref_registry.register_object(self._annotation_to_field(annotation)))
            for name, annotation in wanted_arguments]
        return htypes.params_editor.params_editor(
            target_piece_ref=self._ref_registry.register_object(piece),
            target_command_id=command.id,
            fields=fields,
            )

    def _annotation_to_field(self, annotation):
        if annotation is str:
            return htypes.line.line('')
        assert False, f"Unknown annotation: {annotation!r}"
