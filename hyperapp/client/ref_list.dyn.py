import logging
from operator import attrgetter
from collections import namedtuple

from hyperapp.common.htypes import resource_key_t
from hyperapp.common.ref import ref_repr
from hyperapp.client.module import ClientModule

from . import htypes
from .object_command import command
from .column import Column
from .list_object import ListObject

log = logging.getLogger(__name__)


class RefListObject(ListObject):

    _Item = namedtuple('RefListObject_Item', 'id ref')

    @classmethod
    async def from_state(cls, state, types, async_web, proxy_factory):
        ref_list_service = await RefListService.from_ref(state.ref_list_service, proxy_factory)
        return cls(types, async_web, ref_list_service, state.ref_list_id)

    def __init__(self, types, async_web, ref_list_service, ref_list_id):
        ListObject.__init__(self)
        self._types = types
        self._async_web = async_web
        self._ref_list_service = ref_list_service
        self._ref_list_id = ref_list_id
        self._id2ref = None
        self._item_list = None

    @property
    def title(self):
        return 'Ref List %s' % self._ref_list_id

    @property
    def data(self):
        return htypes.ref_list.dynamic_ref_list(
            ref_list_service=self._ref_list_service.to_ref(),
            ref_list_id=self._ref_list_id,
            )

    @property
    def columns(self):
        return [
            Column('id', is_key=True),
            Column('ref'),
            ]

    async def fetch_items(self, from_key):
        if self._item_list is None:
            ref_list = await self._ref_list_service.get_ref_list(self._ref_list_id)
            self._item_list = [self._Item(ref_item.id, ref_repr(ref_item.ref))
                               for ref_item in ref_list.ref_list]
            self._id2ref = {ref_item.id: ref_item.ref for ref_item in ref_list.ref_list}
        self._distribute_fetch_results(self._item_list)
        self._distribute_eof()

    @command('open', kind='element')
    async def command_open(self, item_id):
        assert self._id2ref is not None  # fetch_element was not called yet
        ref = self._id2ref[item_id]
        log.info('Opening ref %r: %s', item_id, ref_repr(ref))
        return (await self._async_web.summon(ref))


class RefListService(object):

    @classmethod
    async def from_ref(cls, service_ref, proxy_factory):
        proxy = await proxy_factory.from_ref(service_ref)
        return cls(proxy)

    def __init__(self, proxy):
        self._proxy = proxy

    def to_ref(self):
        return self._proxy.service_ref

    async def get_ref_list(self, ref_list_id):
        result = await self._proxy.get_ref_list(ref_list_id)
        return result.ref_list


class ThisModule(ClientModule):

    def __init__(self, module_name, services, config):
        super().__init__(module_name, services)
        services.object_registry.register_actor(
            htypes.ref_list.dynamic_ref_list, RefListObject.from_state, services.types, services.async_web, services.proxy_factory)
