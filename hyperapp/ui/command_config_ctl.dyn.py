from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.config_ctl import MultiItemConfigCtl


class TypeStrCommandKeyCtl:

    def data_to_item(self, piece):
        t = pyobj_creg.invite(piece.t)
        command = web.summon(piece.command)
        return (t, (piece.name, command))

    def item_to_data(self, key, template):
        name, command = template
        return htypes.command.type_str_command(
            t=pyobj_creg.actor_to_ref(key),
            name=name,
            command=mosaic.put(command),
            )


class TypeStrCommandConfigCtl(MultiItemConfigCtl):

    @classmethod
    @mark.actor.config_ctl_creg
    def from_piece(cls, piece):
        return cls()

    def __init__(self):
        super().__init__(key_ctl=TypeStrCommandKeyCtl())

    @property
    def piece(self):
        return htypes.command_config_ctl.type_str_command_config_ctl()

    def config_to_items(self, config_template):
        assert 0 , 'TODO'

    def merge_config(self, dest, src):
        self._merge(dest, src)
        return dest

    def merge_template(self, dest, src):
        self._merge(dest, src)
        return dest

    def _merge(self, dest, src):
        for t, src_name_to_command in src.items():
            dest_name_to_command = dest.setdefault(t, {})
            dest_name_to_command.update(src_name_to_command)

    def resolve(self, system, service_name, config_template):
        assert 0, 'TODO'

    def empty_config_template(self):
        return {}

    def _update_config(self, config_template, key, value_template):
        name, command = value_template
        name_to_command = config_template.setdefault(key, {})
        name_to_command[name] = command
