
class TargetSet:

    def __init__(self):
        self._name_to_target = {}

    def __len__(self):
        return len(self._name_to_target)

    def __getitem__(self, name):
        return self._name_to_target[name]

    def __setitem__(self, name, target):
        self._name_to_target[name] = target

    def enum_ready(self):
        for tgt in self._name_to_target.values():
            if tgt.ready:
                yield tgt
