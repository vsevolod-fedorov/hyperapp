from . import htypes
from .services import (
    mosaic,
    )
from .code.mark import mark
from .code.context import Context
from .code.system_fn import ContextFn
from .code.view_factory import ViewFactory
from .code.multi_actor_template import MultiActorItem
from .tested.code import view_factory_list


def _sample_fn():
    return 'sample-fn'


@mark.fixture
def ctx():
    return Context()


@mark.fixture
def factory(rpc_system_call_factory, format, visualizer_reg):
    system_fn = ContextFn(
        rpc_system_call_factory=rpc_system_call_factory, 
        ctx_params=(),
        service_params=(),
        raw_fn=_sample_fn,
        bound_fn=_sample_fn,
        )
    return ViewFactory(
        format=format,
        visualizer_reg=visualizer_reg,
        k=htypes.view_factory_list_tests.sample_1_k(),
        model_t=None,
        ui_t_t=None,
        view_t=htypes.view_factory_list_tests.sample_view,
        is_wrapper=False,
        view_ctx_params=[],
        system_fn=system_fn,
        )


@mark.fixture
def model_factory(rpc_system_call_factory, format, visualizer_reg):
    system_fn = ContextFn(
        rpc_system_call_factory=rpc_system_call_factory, 
        ctx_params=(),
        service_params=(),
        raw_fn=_sample_fn,
        bound_fn=_sample_fn,
        )
    return ViewFactory(
        format=format,
        visualizer_reg=visualizer_reg,
        k=htypes.view_factory_list_tests.sample_2_k(),
        model_t=htypes.view_factory_list_tests.sample_model_1,
        ui_t_t=None,
        view_t=htypes.view_factory_list_tests.sample_model_1_view,
        is_wrapper=False,
        view_ctx_params=[],
        system_fn=system_fn,
        )


@mark.fixture
def ui_t_factory(rpc_system_call_factory, format, visualizer_reg):
    system_fn = ContextFn(
        rpc_system_call_factory=rpc_system_call_factory, 
        ctx_params=(),
        service_params=(),
        raw_fn=_sample_fn,
        bound_fn=_sample_fn,
        )
    return ViewFactory(
        format=format,
        visualizer_reg=visualizer_reg,
        k=htypes.view_factory_list_tests.sample_3_k(),
        model_t=None,
        ui_t_t=htypes.view_factory_list_tests.sample_ui_t,
        view_t=htypes.view_factory_list_tests.sample_model_2_view,
        is_wrapper=False,
        view_ctx_params=[],
        system_fn=system_fn,
        )


@mark.config_fixture('view_factory_reg')
def view_factory_reg_config(factory, model_factory, ui_t_factory):
    return {
        factory.k: factory,
        model_factory.k: model_factory,
        ui_t_factory.k: ui_t_factory,
        }


@mark.fixture
def piece():
    return htypes.view_factory_list.model(
        model=None,
        )


def test_view_factory_list(ctx, factory, piece):
    items = view_factory_list.view_factory_list(piece, ctx)
    assert items == [factory.item]


@mark.config_fixture('model_reg')
def model_reg_config():
    ui_t = htypes.view_factory_list_tests.sample_ui_t()
    return {
        htypes.view_factory_list_tests.sample_model_2: htypes.model.model(
            ui_t=mosaic.put(ui_t),
            system_fn=mosaic.put(None),
            ),
        }


def test_view_factory_list_with_model(ctx, factory, model_factory):
    piece = htypes.view_factory_list.model(
        model=mosaic.put(htypes.view_factory_list_tests.sample_model_1()),
        )
    items = view_factory_list.view_factory_list(piece, ctx)
    assert set(items) == {factory.item, model_factory.item}


def test_view_factory_list_with_ui_t(ctx, factory, ui_t_factory):
    piece = htypes.view_factory_list.model(
        model=mosaic.put(htypes.view_factory_list_tests.sample_model_2()),
        )
    items = view_factory_list.view_factory_list(piece, ctx)
    assert set(items) == {factory.item, ui_t_factory.item}


def test_open():
    piece = view_factory_list.open_view_factory_list()
    assert isinstance(piece, htypes.view_factory_list.model)


def test_editor_default(ctx):
    context = view_factory_list.pick_view_factory_context(ctx)


def test_selector_get():
    k = htypes.view_factory_list_tests.sample_1_k(),
    value = htypes.view_factory.factory(
        model=None,
        k=mosaic.put(k),
        )
    piece = view_factory_list.view_factory_list_get(value)
    assert piece


def test_selector_pick():
    k = htypes.view_factory_list_tests.sample_1_k(),
    current_item = htypes.view_factory.item(
        k=mosaic.put(k),
        title="<unused>",
        view_t=mosaic.put("<unused>"),
        view_t_str="<unused>",
        is_wrapper=False,
        view_ctx_params=(),
        model_t=None,
        )
    factory = view_factory_list.view_factory_list_pick(piece, current_item)
    assert isinstance(factory, htypes.view_factory.factory)


def test_model_formatter(piece):
    title = view_factory_list.format_model(piece)
    assert type(title) is str
