
class TargetSet:

    def __init__(self, module_list):
        self._path_to_module = {module.path: module for module in module_list}
        self._name_to_target = {}

    def __len__(self):
        return len(self._name_to_target)

    def __getitem__(self, name):
        return self._name_to_target[name]

    def __setitem__(self, name, target):
        self._name_to_target[name] = target

    def enum_runnable(self):
        for tgt in self._name_to_target.values():
            if tgt.runnable:
                yield tgt

    def find_module(self, from_path, sub_path):
        pass # TODO
