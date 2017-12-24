from datetime import datetime
import logging
from pony.orm import db_session, commit, desc, Required, Set
from ..common.diff import SimpleDiff
from ..common.list_object import ListDiff
from ..common.interface import core as core_types
from ..common.interface import hyper_ref as href_types
from ..common.interface import blog as blog_types
from .ponyorm_module import PonyOrmModule
from .util import utcnow, path_part_to_str
from .command import command
from .object import Object, subscription
from .module import ModuleCommand
from . import article
from .list_object import rows2fetched_chunk

log = logging.getLogger(__name__)


MODULE_NAME = 'blog'


class BlogEntry(article.Article):

    #iface = blog_types.blog_entry
    objimpl_id = 'proxy.text'

    def get_path(self):
        return this_module.make_path(self.class_name, path_part_to_str(self.article_id, none_str='new'))

    @command('parent')
    def command_parent(self, request):
        return request.make_response_object(Blog())

    @db_session
    def do_save(self, request, text):
        if self.article_id is not None:
            entry_rec = this_module.BlogEntry[self.article_id]
            entry_rec.text = text
            is_insertion = False
        else:
            entry_rec = this_module.BlogEntry(
                text=text,
                created_at=utcnow())
            is_insertion = True
        commit()
        self.article_id = entry_rec.id  # now may have new get_path()
        log.info('Blog entry is saved, blog entry id = %r', self.article_id)
        subscription.distribute_update(self.iface, self.get_path(), SimpleDiff(text))
        if is_insertion:
            diff = ListDiff.add_one(Blog.rec2element(entry_rec))
            subscription.distribute_update(Blog.iface, Blog.get_path(), diff)
        return request.make_response_result(new_path=self.get_path())


class Blog:#(SmallListObject):

    #iface = blog_types.blog
    objimpl_id = 'proxy_list'
    class_name = 'blog'
    default_sort_column_id = 'id'

    @classmethod
    def resolve(cls, path):
        return cls()

    def __init__(self):
        SmallListObject.__init__(self, core_types)

    @classmethod
    def get_path(cls):
        return this_module.make_path(cls.class_name)

    @command('add')
    def command_add(self, request):
        return request.make_response_object(BlogEntry(mode=BlogEntry.mode_edit))

    @db_session
    def fetch_all_elements(self, request):
        return list(map(self.rec2element, this_module.BlogEntry.select().order_by(desc(this_module.BlogEntry.created_at))))

    @classmethod
    def rec2element(cls, rec):
        commands = [cls.command_open, cls.command_delete]
        return cls.Element(cls.Row(rec.id, rec.created_at), commands)

    @command('open', kind='element')
    def command_open(self, request):
        article_id = request.params.element_key
        return request.make_response_object(BlogEntry(article_id))
    
    @command('delete', kind='element')
    @db_session
    def command_delete(self, request):
        article_id = request.params.element_key
        this_module.BlogEntry[article_id].delete()
        diff = ListDiff.delete(article_id)
        subscription.distribute_update(self.iface, self.get_path(), diff)


class BlogService(Object):

    iface = blog_types.blog_service_iface
    class_name = 'service'

    @classmethod
    def get_path(cls):
        return this_module.make_path(cls.class_name)

    @classmethod
    def resolve(cls, path):
        path.check_empty()
        return cls()

    @command('fetch_blog_contents')
    def command_fetch_blog_contents(self, request):
        all_rows = self.fetch_blog_contents(request.params.blog_id)
        chunk = rows2fetched_chunk('id', all_rows, request.params.fetch_request, blog_types.blog_chunk)
        return request.make_response_result(chunk=chunk)

    @db_session
    def fetch_blog_contents(self, blog_id):
        # blog_id is ignored now
        return list(map(self.rec2element, this_module.BlogEntry.select()))

    @classmethod
    def rec2element(cls, rec):
        ref_list = map(cls.rec2ref, rec.refs.select().order_by(this_module.ArticleRef.id))
        return blog_types.blog_row(
            id=rec.id,
            created_at=rec.created_at,
            title='Article #%d' % rec.id,
            text=rec.text,
            ref_list=list(ref_list),
            )

    @staticmethod
    def rec2ref(rec):
        return blog_types.article_ref(
            id=rec.id,
            title=rec.title,
            href=href_types.href('sha256', rec.href),
            )


class ThisModule(PonyOrmModule):

    def __init__(self, services):
        PonyOrmModule.__init__(self, MODULE_NAME)
        self.article_module = article.this_module

    def init_phase2(self):
        self.Article = self.article_module.Article
        self.ArticleRef = self.article_module.ArticleRef
        self.BlogEntry = self.make_inherited_entity('BlogEntry', self.Article,
                                                    created_at=Required(datetime))
        BlogEntry.register_class(self.BlogEntry)

    def resolve(self, iface, path):
        name = path.pop_str()
        if name == BlogService.class_name:
            return BlogService.resolve(path)
        path.raise_not_found()

    def get_commands(self):
        return [
            ModuleCommand('create', 'Create entry', 'Create new blog entry', None, self.name),
            ModuleCommand('open_blog', 'Blog', 'Open blog', 'Alt+B', self.name),
            ]

    def run_command(self, request, command_id):
        if command_id == 'create':
            return request.make_response_object(BlogEntry())
        if command_id == 'open_blog':
            return request.make_response_object(Blog())
        return PonyOrmModule.run_command(self, request, command_id)
