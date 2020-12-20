from hyperapp.client.module import ClientModule
from . import htypes


class ThisModule(ClientModule):

    def __init__(self, module_name, services, config):
        super().__init__(module_name, services)
        self._ref_registry = services.ref_registry
        services.default_state_builder = self._build_default_state

    def _build_default_state(self):
        piece = htypes.text.text("Welcome to hyperapp")
        piece_ref = self._ref_registry.distil(piece)
        navigator = htypes.navigator.navigator(piece_ref)
        navigator_ref = self._ref_registry.distil(navigator)
        tab_view = htypes.tab_view.tab_view([navigator_ref], 0)
        tab_view_ref = self._ref_registry.distil(tab_view)
        menu_bar = htypes.menu_bar.menu_bar()
        menu_bar_ref = self._ref_registry.distil(menu_bar)
        command_pane = htypes.command_pane.command_pane()
        command_pane_ref = self._ref_registry.distil(command_pane)
        window = htypes.window.window(
            menu_bar_ref=menu_bar_ref,
            command_pane_ref=command_pane_ref,
            central_view_ref=tab_view_ref,
            size=htypes.window.size(1000, 800),
            pos=htypes.window.pos(500, 100))
        window_ref = self._ref_registry.distil(window)
        return htypes.root_layout.root_layout([window_ref])
