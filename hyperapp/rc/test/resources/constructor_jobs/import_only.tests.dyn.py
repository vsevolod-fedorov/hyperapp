from .code.base.mark import mark
from .tested.code import subject


assert subject.value('import only') == 'import only'


@mark.test.constructor
def test_ok():
    pass
