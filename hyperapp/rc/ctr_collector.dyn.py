from collections import namedtuple

from hyperapp.boot.resource.python_module import make_module_name

from .services import (
    mosaic,
    web,
    )


class CtrCollector:

    class Action:
        NotSet = object()
        Ignore = object()
        Mark = namedtuple('Mark', 'module_name')

    def __init__(self, config, marker_ctl):
        self._marker_ctl = marker_ctl
        self._pyname_to_action = {
            make_module_name(mosaic, module_piece): action
            for module_piece, action in config.items()
            }
        self._constructors = []

    def ignore_module(self, module_piece):
        python_module_name = make_module_name(mosaic, module_piece)
        self._pyname_to_action[python_module_name] = self.Action.Ignore

    def get_module_action(self, python_module_name):
        try:
            return self._pyname_to_action[python_module_name]
        except KeyError:
            return self.Action.NotSet

    def init_markers(self):
        for pyname, action in self._pyname_to_action.items():
            if type(action) is self.Action.Mark:
                self._marker_ctl.add_wanted_module(pyname, action.module_name)

    def add_constructor(self, ctr):
        self._constructors.append(ctr)

    @property
    def constructors(self):
        return self._constructors


def resolve_mark_module_cfg_value(piece, key, system, service_name):
    return CtrCollector.Action.Mark(piece.name)


def resolve_ignore_module_cfg_value(piece, key, system, service_name):
    return CtrCollector.Action.Ignore


def ctr_collector(config, marker_ctl):
    collector =  CtrCollector(config, marker_ctl)
    collector.init_markers()
    yield collector
    marker_ctl.clear_wanted_modules()
