from .module import ServerModule


MODULE_NAME = 'remoting_proxy'


class ProxyMethod(object):

    def __init__(self, remoting, service_ref, iface, command):
        self._remoting = remoting
        self._service_ref = service_ref
        self._iface = iface
        self._command = command

    def __call__(self, *args, **kw):
        params = self._command.request(*args, **kw)
        return self._remoting.send_request(self._service_ref, self._iface, self._command, params)


class RemotingProxy(object):

    def __init__(self, remoting, service_ref, iface):
        self._remoting = remoting
        self._service_ref = service_ref
        self._iface = iface

    @property
    def service_ref(self):
        return self._service_ref

    def __getattr__(self, name):
        command = self._iface.get(name)
        if not command:
            raise AttributeError(name)
        return ProxyMethod(self._remoting, self._service_ref, self._iface, command)


class ProxyFactory(object):

    def __init__(self, types, ref_resolver, remoting):
        self._types = types
        self._ref_resolver = ref_resolver
        self._remoting = remoting

    def from_ref(self, ref):
        service = self._ref_resolver.resolve_ref_to_object(ref, expected_type='hyper_ref.service')
        iface = self._types.resolve(service.iface_full_type_name)
        return RemotingProxy(self._remoting, ref, iface)


class ThisModule(ServerModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME)
        services.proxy_factory = ProxyFactory(services.types, services.ref_resolver, services.remoting)