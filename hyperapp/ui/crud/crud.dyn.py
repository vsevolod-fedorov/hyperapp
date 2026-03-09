import logging
import inspect
import weakref
from functools import cached_property

from hyperapp.boot.htypes import TPrimitive

from . import htypes
from .services import (
    deduce_t,
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.context import Context
from .code.ui_model_command import split_command_result
from .code.remote_model import real_model_t
from .code.context_view import ContextView
from .code.record_adapter import FnRecordAdapterBase
from .code.construct_default_form import construct_default_form

log = logging.getLogger(__name__)


def _args_dict_to_tuple(args):
    if args is None:
        return ()
    return tuple(
        htypes.crud.arg(name, mosaic.put(value))
        for name, value in args.items()
        )


def _args_tuple_to_dict(args):
    return {
        arg.name: web.summon(arg.value)
        for arg in args
        }


class CrudContextView(ContextView):

    @classmethod
    @mark.view
    def from_piece(cls, piece, ctx, view_reg, model_layout_reg, crud):
        base_view = view_reg.invite(piece.base_view, ctx)
        model = web.summon_opt(piece.model)
        selector_pick_action = web.summon_opt(piece.selector_pick_action)
        # remote_peer = peer_creg.invite_opt(piece.remote_peer)
        return cls(
            model_layout_reg, crud, base_view, piece.name, model,
            _args_tuple_to_dict(piece.args), selector_pick_action, piece.commit_action, piece.commit_value_field)

    def __init__(
            self, model_layout_reg, crud, base_view, name, model,
            args, selector_pick_action, commit_action_ref, commit_value_field):
        super().__init__(base_view, label=name)
        self._model_layout_reg = model_layout_reg
        self._crud = crud
        self._name = name
        self._model = model
        # self._remote_peer = remote_peer
        self._args = args
        self._selector_pick_action = selector_pick_action
        self._commit_action_ref = commit_action_ref
        self._commit_value_field = commit_value_field
        self._current_layout = self._base_view.piece

    @property
    def piece(self):
        return htypes.crud.view(
            base_view=mosaic.put(self._base_view.piece),
            name=self._name,
            model=mosaic.put_opt(self._model),
            # remote_peer=mosaic.put(self._remote_peer.piece) if self._remote_peer else None,
            # commit_command_d=mosaic.put(self._commit_command_d),
            args=_args_dict_to_tuple(self._args),
            selector_pick_action=mosaic.put_opt(self._selector_pick_action),
            commit_action=self._commit_action_ref,
            commit_value_field=self._commit_value_field,
            )

    async def children_changed(self, ctx, rctx, widget, save_layout):
        layout = self._base_view.piece
        if save_layout and layout != self._current_layout:
            self._set_layout(layout)

    def _set_layout(self, layout):
        layout_k = self._crud.layout_k(self._model, self._name)
        log.info("CRUD context view: set new layout: %s -> %s", layout_k, layout)
        self._model_layout_reg[layout_k] = layout
        self._current_layout = self._base_view.piece

    @property
    def commit_command(self):
        if self._name == 'edit':
            name = 'save'
        else:
            name = self._name
        command_key = htypes.crud.commit_command_key(
            model=mosaic.put_opt(self._model),
            name=name,
            )
        command = htypes.crud.commit_command(
            model=mosaic.put_opt(self._model),
            args=_args_dict_to_tuple(self._args),
            selector_pick_action=mosaic.put_opt(self._selector_pick_action),
            commit_action=self._commit_action_ref,
            commit_value_field=self._commit_value_field,
            )
        return (command_key, name, command)


@mark.ctx_actor.command_creg
async def open_command(piece, model, current_item, navigator, ctx, crud):
    value_t = pyobj_creg.invite(piece.value_t)
    args = {
        name: getattr(current_item, name)
        for name in piece.key_fields
        }
    await crud.open_view(
        navigator_rec=navigator,
        ctx=ctx,
        value_t=value_t,
        name=piece.name,
        init_action_ref=piece.init_action,
        commit_action_ref=piece.commit_action,
        commit_value_field='value',
        model=model,
        init_args=args,
        commit_args=args,
        )


class CrudRecordAdapter(FnRecordAdapterBase):

    @classmethod
    @mark.actor.ui_adapter_creg
    def from_piece(cls, piece, model, ctx, client_feed_factory, crud_init_action_creg, crud):
        record_t = pyobj_creg.invite(model.record_t)
        value = cls._get_shared_value(model, record_t)
        src_model = web.summon(model.model)
        init_action_ref = model.init_action
        args = _args_tuple_to_dict(model.args)
        return cls(client_feed_factory, crud_init_action_creg,
                   model, record_t, ctx, value, crud, src_model, init_action_ref, args)

    def __init__(self, client_feed_factory, crud_init_action_creg,
                 model, record_t, ctx, value, crud, src_model, init_action_ref, args):
        super().__init__(client_feed_factory, model, record_t, ctx, value)
        self._crud_init_action_creg = crud_init_action_creg
        self._crud = crud
        self._src_model = src_model
        self._args = args
        self._init_action_ref = init_action_ref

    def _get_value(self):
        fn_ctx = self._crud.fn_ctx(self._ctx, self._src_model, self._args)
        return self._crud_init_action_creg.invite(self._init_action_ref, fn_ctx)


class Crud:

    def __init__(
            self, canned_ctl_item_factory, visualizer, view_reg, selector_reg, model_layout_reg,
            selector_open_action_creg, crud_init_action_creg):
        self._canned_ctl_item_factory = canned_ctl_item_factory
        self._visualizer = visualizer
        self._view_reg = view_reg
        self._selector_reg = selector_reg
        self._model_layout_reg = model_layout_reg
        self._selector_open_action_creg = selector_open_action_creg
        self._crud_init_action_creg = crud_init_action_creg

    def fn_ctx(self, ctx, model, args, kw=None):
        if args is None:
            args = {}
        if model is not None:
            model_layout_kw = {
                'model': model,
                }
        else:
            model_layout_kw = {}
        all_kw = {
            **model_layout_kw,
            **args,
            **self._canned_kw(ctx, args),
            **(kw or {}),
            }
        return ctx.clone_with(**all_kw)

    def layout_k(self, model, name):
        model_t = deduce_t(model)
        return htypes.crud.layout_k(
            model_t=pyobj_creg.actor_to_ref(model_t),
            name=name,
            )

    async def open_view(
            self,
            navigator_rec,
            ctx,
            value_t,
            name,
            init_action_ref,
            commit_action_ref,
            commit_value_field,
            model,
            # remote_peer=None,
            init_args=None,
            commit_args=None,
            ):
        try:
            selector = self._selector_reg[value_t]
        except KeyError:
            selector_open_action = None
            selector_pick_action = None
        else:
            selector_open_action = selector.open_action
            selector_pick_action = selector.pick_action
        if selector_pick_action:
            if init_action_ref is None:
                value = None
            else:
                value = self._run_init(ctx, init_action_ref, model, init_args)
                action_ctx = ctx.clone_with(value=value)
            selector_result = self._selector_open_action_creg.animate(selector_open_action, action_ctx)
            selector_model, key = split_command_result(selector_result)
            selector_model_t = real_model_t(selector_model)
            base_view_piece = await self._visualizer(ctx, selector_model_t)
            new_model = selector_model
        else:
            assert init_action_ref  # Init action fn may be omitted only for selectors.
            layout_k = self.layout_k(model, name)
            try:
                base_view_piece = self._model_layout_reg[layout_k]
            except KeyError:
                if isinstance(value_t, TPrimitive):
                    base_view_piece = await self._primitive_view(ctx, value_t)
                else:
                    base_view_piece = await self._form_view(ctx, value_t)
            if isinstance(value_t, TPrimitive):
                new_model = self._run_init(ctx, init_action_ref, model, init_args)
            else:
                new_model = htypes.crud.form_model(
                    model=mosaic.put(model),
                    record_t=pyobj_creg.actor_to_ref(value_t),
                    init_action=init_action_ref,
                    args=_args_dict_to_tuple(commit_args),
                    )
            key = None
        new_view_piece = htypes.crud.view(
            base_view=mosaic.put(base_view_piece),
            name=name,
            model=mosaic.put(model),
            # remote_peer=mosaic.put(remote_peer.piece) if remote_peer else None,
            args=_args_dict_to_tuple(commit_args),
            selector_pick_action=mosaic.put_opt(selector_pick_action),
            commit_action=commit_action_ref,
            commit_value_field=commit_value_field,
            )
        new_ctx = ctx.clone_with(
            model=new_model,
            )
        new_view = self._view_reg.animate(new_view_piece, new_ctx)
        navigator_widget = navigator_rec.widget_wr()
        if navigator_widget is None:
            raise RuntimeError("Navigator widget is gone")
        await navigator_rec.view.open(ctx, new_model, new_view, navigator_widget, key=key, set_layout=False)

    # Override context with original elements, canned by args picker.
    def _canned_kw(self, ctx, args):
        kw = {}
        try:
            item_piece = args['canned_item_piece']
        except KeyError:
            pass
        else:
            item = self._canned_ctl_item_factory(item_piece, ctx)
            if item:  # None if view&widget are already gone.
                kw['hook'] = item.hook
                kw['widget'] = weakref.ref(item.widget)
                kw['view'] = item.view
        try:
            model_state = args['model_state']
        except KeyError:
            pass
        else:
            kw.update(Context.attributes(model_state))
        return kw

    async def _form_view(self, ctx, value_t):
        adapter = htypes.crud.record_adapter()
        return await construct_default_form(self._visualizer, ctx, adapter, value_t)

    async def _primitive_view(self, ctx, value_t):
        return await self._visualizer(ctx, value_t)

    def _run_init(self, ctx, init_action_ref, model, args):
        fn_ctx = self.fn_ctx(ctx, model, args)
        return self._crud_init_action_creg.invite(init_action_ref, fn_ctx)


@mark.service
def crud(canned_ctl_item_factory, visualizer, view_reg, selector_reg, model_layout_reg,
         selector_open_action_creg, crud_init_action_creg):
    return Crud(canned_ctl_item_factory, visualizer, view_reg, selector_reg, model_layout_reg,
                selector_open_action_creg, crud_init_action_creg)


@mark.ctx_actor.command_creg
def commit_command(piece, model, ctx, selector_pick_action_creg, crud_commit_action_creg, crud):
    args = _args_tuple_to_dict(piece.args)
    src_model = web.summon(piece.model)
    fn_ctx = crud.fn_ctx(ctx, model, args)
    if piece.selector_pick_action:
        value = selector_pick_action_creg.invite(piece.selector_pick_action, fn_ctx)
    else:
        value = fn_ctx.value
    action_ctx = fn_ctx.clone_with({
        'model': src_model,
        piece.commit_value_field: value,
        })
    return crud_commit_action_creg.invite(piece.commit_action, action_ctx)


@mark.ui_command_enum
def crud_commit_command_enum(view, ctx, command_factory):
    key, name, command = view.commit_command
    return [command_factory(
        key=key,
        name=name,
        command=command,
        ctx=ctx.pop(),
        )]


@mark.actor.resource_name_creg
def layout_k_resource_name(piece, gen):
    model_mt = web.summon(piece.model_t)
    model_mt_name = gen.assigned_name(model_mt).replace(':', '-')
    return f'crud-layout_k-{model_mt_name}-{piece.name}'


@mark.actor.formatter_creg
def format_layout_k(piece, format):
    model_t = pyobj_creg.invite(piece.model_t)
    model_t_title = format(model_t)
    return f'crud.layout_k({model_t_title}/{piece.name})'
