from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.rc_resource import Resource


class ImportResource(Resource):

    @classmethod
    def for_type(cls, module_name, name, piece):
        import_name = ['htypes', module_name, name]
        return cls('', import_name, piece)

    @classmethod
    def from_piece(cls, piece):
        return cls(
            module_name=piece.module_name,
            import_name=piece.import_name,
            resource=web.summon(piece.resource),
            )

    def __init__(self, module_name, import_name, resource):
        self._module_name = module_name
        self._import_name = tuple(import_name)
        self._resource = resource

    def __eq__(self, rhs):
        return (
            self.__class__ is rhs.__class__
            and self._module_name == rhs._module_name
            and self._import_name == rhs._import_name
            and self._resource == rhs._resource
            )

    def __hash__(self):
        return hash(('import-resource', self._module_name, self._import_name, self._resource))

    @property
    def piece(self):
        return htypes.import_resource.import_resource(
            module_name=self._module_name,
            import_name=self._import_name,
            resource=mosaic.put(self._resource),
            )

    @property
    def import_records(self):
        return [htypes.builtin.import_rec(
            full_name='.'.join(self._import_name),
            resource=mosaic.put(self._resource),
            )]

    @property
    def system_config_items(self):
        template = htypes.import_resource.import_template(
            import_name=self._import_name,
            resource=mosaic.put(self._resource),
            )
        cfg_item = htypes.import_resources.import_key_cfg_item(
            module_name=self._module_name,
            import_name=self._import_name,
            value=mosaic.put(template),
            )
        return {'import_recorder_reg': [cfg_item]}
