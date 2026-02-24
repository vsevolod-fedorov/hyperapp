from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.mark import mark
from .tested.code import selector as selector_module


@mark.fixture.obj
def template_piece():
    return htypes.selector.template(
        model_t=pyobj_creg.actor_to_ref(htypes.selector_tests.sample_model),
        open_action=mosaic.put(htypes.selector_tests.sample_open_action()),
        pick_action=mosaic.put(htypes.selector_tests.sample_pick_action()),
        )


def test_template(system, template_piece):
    selector = selector_module.resolve_selector_cfg_value(
        template_piece, "<unused key>", system, "<unused service name>")
    assert isinstance(selector, selector_module.Selector)
