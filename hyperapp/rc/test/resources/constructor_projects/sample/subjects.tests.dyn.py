from .tested.code import subject
from .tested.code.lib import subject as library_subject


assert library_subject.value('import') == 'import'


def test_both():
    assert subject.value() == 'local'
    assert library_subject.value('test') == 'test'
