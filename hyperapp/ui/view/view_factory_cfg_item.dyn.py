from .services import (
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.view_factory import ViewFactory, ViewMultiFactory


class ViewFactoryTemplate:

    @classmethod
    @mark.actor.cfg_item_creg
    def from_piece(cls, piece):
        if piece.model_t_list is not None:
            model_t_list = [
                pyobj_creg.invite(model_t) for model_t in piece.model_t_list
                ]
        else:
            model_t_list = None
        return cls(
            k=web.summon(piece.k),
            model_t_list=model_t_list,
            ui_t_t=pyobj_creg.invite_opt(piece.ui_t_t),
            view_t=pyobj_creg.invite(piece.view_t),
            is_wrapper=piece.is_wrapper,
            view_ctx_params=piece.view_ctx_params,
            system_fn=web.summon(piece.system_fn),
            )

    def __init__(self, k, model_t_list, ui_t_t, view_t, is_wrapper, view_ctx_params, system_fn):
        assert not (model_t_list is not None and ui_t_t is not None)  # Not both.
        self._k = k
        self._model_t_list = model_t_list
        self._ui_t_t = ui_t_t
        self._view_t = view_t
        self._is_wrapper = is_wrapper
        self._view_ctx_params = view_ctx_params
        self._system_fn = system_fn

    @property
    def key(self):
        return self._k

    def resolve(self, system, service_name):
        system_fn_creg = system['system_fn_creg']
        return ViewFactory(
            format=system['format'],
            visualizer_reg=system['visualizer_reg'],
            k=self._k,
            model_t_list=self._model_t_list,
            ui_t_t=self._ui_t_t,
            view_t=self._view_t,
            is_wrapper=self._is_wrapper,
            view_ctx_params=self._view_ctx_params,
            system_fn=system_fn_creg.animate(self._system_fn),
            )


class ViewFactoryMultiTemplate:

    @classmethod
    @mark.actor.cfg_item_creg
    def from_piece(cls, piece):
        if piece.model_t_list is not None:
            model_t_list = [
                pyobj_creg.invite(model_t) for model_t in piece.model_t_list
                ]
        else:
            model_t_list = None
        return cls(
            k=web.summon(piece.k),
            model_t_list=model_t_list,
            ui_t_t=pyobj_creg.invite_opt(piece.ui_t_t),
            list_fn=web.summon(piece.list_fn),
            get_fn=web.summon(piece.get_fn),
            )

    def __init__(self, k, model_t_list, ui_t_t, list_fn, get_fn):
        assert not (model_t_list is not None and ui_t_t is not None)  # Not both.
        self._k = k
        self._model_t_list = model_t_list
        self._ui_t_t = ui_t_t
        self._list_fn = list_fn
        self._get_fn = get_fn

    @property
    def key(self):
        return self._k

    def resolve(self, system, service_name):
        system_fn_creg = system['system_fn_creg']
        return ViewMultiFactory(
            format=system['format'],
            visualizer_reg=system['visualizer_reg'],
            k=self._k,
            model_t_list=self._model_t_list,
            ui_t_t=self._ui_t_t,
            list_fn=system_fn_creg.animate(self._list_fn),
            get_fn=system_fn_creg.animate(self._get_fn),
            )
