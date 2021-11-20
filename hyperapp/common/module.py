import logging

log = logging.getLogger(__name__)


MAX_INIT_PHASE_COUNT = 3


# base class for modules
class Module(object):

    def __init__(self, name, services, config):
        self.name = name

    def __repr__(self):
        return '<Module %r>' % self.name


class ModuleRegistry(object):

    def __init__(self):
        self._module_list = []  # import order should be preserved

    def register(self, module):
        assert isinstance(module, Module), repr(module)
        self._module_list.append(module)

    def init_phases(self, services):
        for phase_num in range(1, MAX_INIT_PHASE_COUNT + 1):
            for module in self._module_list:
                method = getattr(module, 'init_phase_{}'.format(phase_num), None)
                if method:
                    log.info('Run init phase %d for %r', phase_num, module)
                    method(services)

    def enum_modules_method(self, method_name):
        for module in self._module_list:
            method = getattr(module, method_name, None)
            if method:
                yield (module, method)
