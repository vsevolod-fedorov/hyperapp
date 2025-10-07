from . import htypes


class SingleStructCtl:

    @classmethod
    def from_piece(cls, piece):
        return cls()

    @property
    def piece(self):
        return htypes.system.single_struct_ctl()

    @staticmethod
    def config_to_items(config_template):
        return config_template.items()

    @staticmethod
    def merge(dest, src):
        dest.update(src)

    @staticmethod
    def update_config(config_template, key, value_template):
        config_template[key] = value_template

    @staticmethod
    def resolve_value(value_ctl, system, service_name, key, value_template):
        return value_ctl.resolve(value_template, key, system, service_name)


class ListStructCtl:

    @classmethod
    def from_piece(cls, piece):
        return cls()

    @property
    def piece(self):
        return htypes.system.list_struct_ctl()

    @staticmethod
    def config_to_items(config_template):
        items = []
        for key, value_list in config_template.items():
            for value in value_list:
                items.append((key, value))
        return items

    @staticmethod
    def merge(dest, src):
        for key, value_list in src.items():
            dest.setdefault(key, []).extend(value_list)

    @staticmethod
    def update_config(config_template, key, value_template):
        config_template.setdefault(key, []).append(value_template)

    @staticmethod
    def resolve_value(value_ctl, system, service_name, key, value_template):
        return [
            value_ctl.resolve(elt, key, system, service_name)
            for elt in value_template
            ]


def config_struct_ctl_creg_config():
    return {
        htypes.system.single_struct_ctl: SingleStructCtl.from_piece,
        htypes.system.list_struct_ctl: ListStructCtl.from_piece,
        }
