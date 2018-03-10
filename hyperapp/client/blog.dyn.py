import logging

from ..common.htypes import tInt, tDateTime, Column, list_handle_type
from ..common.url import Url
from ..common.interface import core as core_types
from ..common.interface import hyper_ref as href_types
from ..common.interface import blog as blog_types
from ..common.interface import line_object as line_object_types
from ..common.interface import text_object_types
from ..common.interface import form as form_types
from ..common.interface import object_selector as object_selector_types
from ..common.list_object import Element, Chunk
from .module import Module
from .command import command
from .text_object import TextObject
from .list_object import ListObject
from .form import FormObject
from . import object_selector

log = logging.getLogger(__name__)


class BlogObject(ListObject):

    impl_id = 'blog'

    @classmethod
    def from_state(cls, state, ref_registry, handle_resolver):
        blog_service = this_module.blog_service_from_data(state.blog_service)
        return cls(ref_registry, handle_resolver, blog_service, state.blog_id)

    def __init__(self, ref_registry, handle_resolver, blog_service, blog_id):
        ListObject.__init__(self)
        self._ref_registry = ref_registry
        self._handle_resolver = handle_resolver
        self._blog_service = blog_service
        self._blog_id = blog_id

    def get_state(self):
        return blog_types.blog_object(self.impl_id, self._blog_service.to_data(), self._blog_id)

    def get_title(self):
        return self._blog_id

    def pick_current_refs(self):
        return []

    def get_columns(self):
        return [
            Column('id', type=tInt, is_key=True),
            Column('created_at', type=tDateTime),
            Column('title'),
            ]

    def get_key_column_id(self):
        return 'id'

    async def fetch_elements_impl(self, sort_column_id, from_key, desc_count, asc_count):
        chunk = await self._blog_service.fetch_blog_contents(
            self._blog_id, sort_column_id, from_key, desc_count, asc_count)
        elements = [Element(row.id, row, commands=None, order_key=getattr(row, sort_column_id))
                    for row in chunk.rows]
        return Chunk(sort_column_id, from_key, elements, chunk.bof, chunk.eof)

    def process_diff(self, diff):
        assert isinstance(diff, ListDiff), repr(diff)
        log.info('-- BlogObject.process_diff self=%r diff=%r', id(self), diff)

    @command('open', kind='element')
    async def command_open(self, element_key):
        return (await self._open_article(article_id=element_key))

    @command('add')
    async def command_add(self):
        article_id = await self._blog_service.create_article(self._blog_id)
        return (await self._open_article(article_id))

    async def _open_article(self, article_id):
        blog_service_ref = self._blog_service.to_ref()
        object = blog_types.blog_article_ref(blog_service_ref, self._blog_id, article_id)
        ref = self._ref_registry.register_new_object(blog_types.blog_article_ref, object)
        return (await self._handle_resolver.resolve(ref))


class BlogArticleForm(FormObject):

    impl_id = 'blog_article_form'

    @classmethod
    async def from_state(cls, state, field_object_map, ref_registry, handle_resolver):
        blog_service = this_module.blog_service_from_data(state.blog_service)
        row = await blog_service.get_blog_row(state.blog_id, state.article_id)
        return cls(field_object_map, ref_registry, handle_resolver, blog_service, state.blog_id, state.article_id, row)

    def __init__(self, field_object_map, ref_registry, handle_resolver, blog_service, blog_id, article_id, row):
        super().__init__(field_object_map)
        self._ref_registry = ref_registry
        self._handle_resolver = handle_resolver
        self._blog_service = blog_service
        self._blog_id = blog_id
        self._article_id = article_id
        self._row = row
        self._fields['title'].line = row.title
        self._fields['text'].init(handle_resolver, blog_service, blog_id, article_id, row)

    def get_title(self):
        return self._row.title

    def get_state(self):
        return blog_types.blog_article_form(self.impl_id, self._blog_service.to_data(), self._blog_id, self._article_id)

    @command('refs')
    async def command_refs(self):
        blog_service_ref = self._blog_service.to_ref()
        object = blog_types.blog_article_ref_list_ref(blog_service_ref, self._blog_id, self._article_id)
        ref = self._ref_registry.register_new_object(blog_types.blog_article_ref_list_ref, object)
        return (await self._handle_resolver.resolve(ref))

    @command('save')
    async def command_save(self):
        title = self._fields['title'].line
        text = self._fields['text'].text
        await self._blog_service.save_article(self._blog_id, self._article_id, title, text)


class BlogArticleContents(TextObject):

    impl_id = 'blog_article_contents'

    def __init__(self, text):
        super().__init__(text)
        self._handle_resolver = None
        self._blog_service = None
        self._blog_id = None
        self._article_id = None
        self._row = None

    def init(self, handle_resolver, blog_service, blog_id, article_id, row):
        self._handle_resolver = handle_resolver
        self._blog_service = blog_service
        self._blog_id = blog_id
        self._article_id = article_id
        self._row = row
        self.text = row.text

    def get_title(self):
        if self._row:
            return self._row.title
        else:
            return None

    async def open_ref(self, id):
        log.info('Opening ref: %r', id)
        id2ref = {ref.id: ref.ref for ref in self._row.ref_list}
        ref = id2ref.get(int(id))
        if not ref:
            log.warning('Blog %r article#%d has missing ref inside its text: %r', self._blog_id, self._article_id, id)
            return
        return (await self._handle_resolver.resolve(ref))


class ArticleRefListObject(ListObject):

    impl_id = 'article-ref-list'

    @classmethod
    def from_state(cls, state, ref_registry, handle_resolver):
        blog_service = this_module.blog_service_from_data(state.blog_service)
        return cls(ref_registry, handle_resolver, blog_service, state.blog_id, state.article_id)

    def __init__(self, ref_registry, handle_resolver, blog_service, blog_id, article_id):
        ListObject.__init__(self)
        self._ref_registry = ref_registry
        self._handle_resolver = handle_resolver
        self._blog_service = blog_service
        self._blog_id = blog_id
        self._article_id = article_id
        self._id2ref = {}

    def get_state(self):
        return blog_types.article_ref_list_object(self.impl_id, self._blog_service.to_data(), self._blog_id, self._article_id)

    def get_title(self):
        return 'refs for %s:%d' % (self._blog_id, self._article_id)

    def pick_current_refs(self):
        return []

    def get_columns(self):
        return [
            Column('id', type=tInt, is_key=True),
            Column('title'),
            Column('ref'),
            ]

    def get_key_column_id(self):
        return 'id'

    async def fetch_elements_impl(self, sort_column_id, from_key, desc_count, asc_count):
        ref_list = await self._blog_service.get_article_ref_list(self._blog_id, self._article_id)
        self._id2ref.update({row.id: row.ref for row in ref_list})
        elements = [Element(row.id, row, commands=None, order_key=getattr(row, sort_column_id))
                    for row in ref_list]
        return Chunk(sort_column_id, from_key=None, elements=elements, bof=True, eof=True)

    async def get_ref_handle(self, id):
        ref = self._id2ref[id]
        return (await self._handle_resolver.resolve(ref))

    @command('open', kind='element')
    async def command_open(self, element_key):
        return (await self.get_ref_handle(element_key))

    @command('add')
    async def command_add(self):
        blog_service_ref = self._blog_service.to_ref()
        article_ref_list_object = blog_types.blog_article_ref_list_ref(blog_service_ref, self._blog_id, self._article_id)
        target_ref = self._ref_registry.register_new_object(blog_types.blog_article_ref_list_ref, article_ref_list_object)
        target_handle = await self._handle_resolver.resolve(target_ref)
        callback = blog_types.selector_callback(self._blog_service.to_data(), self._blog_id, self._article_id)
        object = object_selector_types.object_selector_object('object_selector', callback)
        return object_selector_types.object_selector_view('object_selector', object, target_handle)

    @command('change', kind='element')
    async def command_change(self, element_key):
        target_handle = await self.get_ref_handle(element_key)
        callback = blog_types.selector_callback(self._blog_service.to_data(), self._blog_id, self._article_id, element_key)
        object = object_selector_types.object_selector_object('object_selector', callback)
        return object_selector_types.object_selector_view('object_selector', object, target_handle)

    @command('delete', kind='element')
    async def command_delete(self, element_key):
        await self._blog_service.delete_ref(self._blog_id, self._article_id, element_key)


class SelectorCallback(object):

    @classmethod
    def from_data(cls, state, ref_registry, handle_resolver):
        blog_service = this_module.blog_service_from_data(state.blog_service)
        return cls(ref_registry, handle_resolver, blog_service, state.blog_id, state.article_id, state.ref_id)

    def __init__(self, ref_registry, handle_resolver, blog_service, blog_id, article_id, ref_id):
        self._ref_registry = ref_registry
        self._handle_resolver = handle_resolver
        self._blog_service = blog_service
        self._blog_id = blog_id
        self._article_id = article_id
        self._ref_id = ref_id

    async def set_ref(self, title, ref):
        if self._ref_id is not None:
            await self._blog_service.update_ref(self._blog_id, self._article_id, self._ref_id, title, ref)
            ref_id = self._ref_id
        else:
            ref_id = await self._blog_service.add_ref(self._blog_id, self._article_id, title, ref)
        blog_service_ref = self._blog_service.to_ref()
        object = blog_types.blog_article_ref_list_ref(blog_service_ref, self._blog_id, self._article_id, ref_id)
        ref = self._ref_registry.register_new_object(blog_types.blog_article_ref_list_ref, object)
        return (await self._handle_resolver.resolve(ref))

    def to_data(self):
        return blog_types.selector_callback(self._blog_service.to_data(), self._blog_id, self._article_id, self._ref_id)
    

class BlogService(object):

    def __init__(self, ref_registry, service_proxy):
        self._ref_registry = ref_registry
        self._service_proxy = service_proxy
        self._blog_id_article_id_to_row = {}  # (blog_id, article_id) -> blog_row, already fetched rows

    def to_data(self):
        service_url = self._service_proxy.get_url()
        return blog_types.blog_service(service_url.to_data())

    def to_ref(self):
        object = blog_types.blog_service(service_url=self._service_proxy.get_url().to_data())
        return self._ref_registry.register_new_object(blog_types.blog_service, object)

    async def fetch_blog_contents(self, blog_id, sort_column_id, from_key, desc_count, asc_count):
        fetch_request = blog_types.row_fetch_request(sort_column_id, from_key, desc_count, asc_count)
        result = await self._service_proxy.fetch_blog_contents(blog_id, fetch_request)
        self._blog_id_article_id_to_row.update({(blog_id, row.id): row for row in result.chunk.rows})
        return result.chunk

    async def get_blog_row(self, blog_id, article_id):
        row = self._blog_id_article_id_to_row.get((blog_id, article_id))
        if not row:
            await self.fetch_blog_contents(blog_id, sort_column_id='id', from_key=article_id, desc_count=1, asc_count=0)
            row = self._blog_id_article_id_to_row.get((blog_id, article_id))
            assert row, repr((blog_id, article_id))  # expecting it to be fetched now
        return row

    async def create_article(self, blog_id):
        result = await self._service_proxy.create_article(blog_id)
        row = result.blog_row
        self._blog_id_article_id_to_row[(blog_id, row.id)] = row
        return row.id

    async def save_article(self, blog_id, article_id, title, text):
        await self._service_proxy.save_article(blog_id, article_id, title, text)

    async def get_article_ref_list(self, blog_id, article_id):
        row = await self.get_blog_row(blog_id, article_id)
        return row.ref_list

    async def update_ref(self, blog_id, article_id, ref_id, title, ref):
        await self._service_proxy.update_ref(blog_id, article_id, ref_id, title, ref)

    async def add_ref(self, blog_id, article_id, title, ref):
        result = await self._service_proxy.add_ref(blog_id, article_id, title, ref)
        return result.ref_id

    async def delete_ref(self, blog_id, article_id, ref_id):
        await self._service_proxy.delete_ref(blog_id, article_id, ref_id)


class ThisModule(Module):

    def __init__(self, services):
        Module.__init__(self, services)
        self._iface_registry = services.iface_registry
        self._ref_registry = services.ref_registry
        self._ref_resolver = services.ref_resolver
        self._proxy_factory = services.proxy_factory
        self._url2service = {}
        services.handle_registry.register(blog_types.blog_ref, self.resolve_blog_object)
        services.handle_registry.register(blog_types.blog_article_ref, self.resolve_blog_article_object)
        services.handle_registry.register(blog_types.blog_article_ref_list_ref, self.resolve_blog_article_ref_list_object)
        services.objimpl_registry.register(
            BlogObject.impl_id, BlogObject.from_state, services.ref_registry, services.handle_resolver)
        services.form_impl_registry.register(
            BlogArticleForm.impl_id, BlogArticleForm.from_state, services.ref_registry, services.handle_resolver)
        services.objimpl_registry.register(
            BlogArticleContents.impl_id, BlogArticleContents.from_state, services.handle_resolver)
        services.objimpl_registry.register(
            ArticleRefListObject.impl_id, ArticleRefListObject.from_state, services.ref_registry, services.handle_resolver)
        object_selector.this_module.register_callback(
            blog_types.selector_callback, SelectorCallback.from_data, services.ref_registry, services.handle_resolver)

    def blog_service_from_data(self, service_object):
        service_url = Url.from_data(self._iface_registry, service_object.service_url)
        service = self._url2service.get(service_url)
        if not service:
            service_proxy = self._proxy_factory.from_url(service_url)
            service = BlogService(self._ref_registry, service_proxy)
            self._url2service[service_url] = service
        return service

    async def resolve_blog_object(self, blog_object):
        blog_service = await self._ref_resolver.resolve_ref_to_object(blog_object.blog_service_ref)
        list_object = blog_types.blog_object(BlogObject.impl_id, blog_service, blog_object.blog_id)
        handle_t = list_handle_type(core_types, tInt)
        sort_column_id = 'created_at'
        resource_id = ['client_module', 'blog', 'BlogObject']
        return handle_t('list', list_object, resource_id, sort_column_id, key=None)

    async def resolve_blog_article_object(self, blog_article_object):
        blog_service = await self._ref_resolver.resolve_ref_to_object(blog_article_object.blog_service_ref)
        title_object = line_object_types.line_object('line', '')
        title_view = line_object_types.line_edit_view('line_edit', title_object)
        contents_object = text_object_types.text_object(BlogArticleContents.impl_id, '')
        contents_view = core_types.obj_handle('text_view', contents_object)
        form_object = blog_types.blog_article_form(
            BlogArticleForm.impl_id, blog_service, blog_article_object.blog_id, blog_article_object.article_id)
        form_view = form_types.form_handle('form', form_object, [
            form_types.form_view_field('title', title_view),
            form_types.form_view_field('text', contents_view),
            ], current_field_id='text')
        return form_view

    async def resolve_blog_article_ref_list_object(self, ref_list_object):
        blog_service = await self._ref_resolver.resolve_ref_to_object(ref_list_object.blog_service_ref)
        list_object = blog_types.article_ref_list_object(
            ArticleRefListObject.impl_id, blog_service, ref_list_object.blog_id, ref_list_object.article_id)
        handle_t = list_handle_type(core_types, tInt)
        sort_column_id = 'id'
        resource_id = ['client_module', 'blog', 'BlogArticleRefListObject']
        return handle_t('list', list_object, resource_id, sort_column_id, key=None)
