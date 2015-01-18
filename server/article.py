import json
from pony.orm import db_session, Required, Optional, Set
from util import str2id
from object import Object, ListObject, Command, Element, Column
from module import ModuleCommand
from ponyorm_module import PonyOrmModule
from iface import Iface, TextObjectIface, ListIface


MODULE_NAME = 'article'


class Article(Object):

    iface = TextObjectIface()
    view_id = 'text'

    def __init__( self, path, article_id ):
        Object.__init__(self, path)
        self.article_id = article_id

    @classmethod
    def from_path( cls, path ):
        article_id = path['article_id']
        return cls(path, article_id=article_id)

    @db_session
    def get_json( self ):
        if self.article_id is not None:
            rec = module.Article[self.article_id]
            text = rec.text
        else:
            text = None
        return dict(
            Object.get_json(self),
            text=text)

    def get_commands( self ):
        return [
            Command('save', 'Save', 'Save article', 'Ctrl+S'),
            Command('refs', 'Refs', 'Open article references', 'Ctrl+R'),
            ]

    def run_command( self, command_id, request ):
        if command_id == 'save':
            return self.run_command_save(request)
        elif command_id == 'refs':
            return self.run_command_refs(request)
        else:
            return Object.run_command(self, command_id, request)

    def run_command_save( self, request ):
        text = request['text']
        new_path = self.do_save(text)
        return dict(new_path=new_path)

    def run_command_refs( self, request ):
        return ArticleRefList.make(self.article_id)

    def do_save( self, text ):
        with db_session:
            if self.article_id is not None:
                article_rec = module.Article[self.article_id]
            else:
                article_rec = None
            article_rec = self.save_article(article_rec, text)
        print 'Article is saved, article_id =', article_rec.id
        return dict(self.path, article_id=article_rec.id)

    def save_article( self, article_rec, text ):
        if article_rec is not None:
            article_rec.text = text
        else:
            article_rec = module.Article(text=text)
        return article_rec


class ArticleRefList(ListObject):

    iface = ListIface()
    view_id = 'list'

    columns = [
        Column('key', 'Ref id'),
        Column('path', 'Path'),
        ]

    def __init__( self, path, article_id ):
        ListObject.__init__(self, path)
        self.article_id = article_id

    @classmethod
    def make( cls, article_id ):
        path = module.make_path(object='article_ref_list', article_id=article_id)
        return cls(path, article_id)

    @classmethod
    def from_path( cls, path ):
        article_id = path['article_id']
        return cls(path, article_id)

    def get_commands( self ):
        return [Command('add', 'Add ref', 'Create new reference', 'Ins')]

    def run_command( self, command_id, request ):
        if command_id == 'add':
            return ArticleRef.make(self.article_id, ref_id=None)
        assert False, repr(command_id)  # Unsupported command

    @db_session
    def get_all_elements( self ):
        return map(self.rec2element, module.Article[self.article_id].refs)

    def rec2element( self, rec ):
        commands = [
            Command('open', 'Open', 'Open article reference'),
            Command('select', 'Select', 'Open reference selector', 'Space'),
            Command('delete', 'Delete', 'Delete article reference', 'Del'),
            ]
        return Element(rec.id, [rec.id, rec.path], commands)

    def run_element_command( self, command_id, element_key ):
        if command_id == 'open':
            return ArticleRef.make(self.article_id, ref_id=element_key)
        if command_id == 'select':
            return RefSelector.make(self.article_id, ref_id=element_key)
        if command_id == 'delete':
            return self.run_element_command_delete(element_key)
        return ListObject.run_element_command(self, command_id, element_key)

    @db_session
    def run_element_command_delete( self, ref_id ):
        module.ArticleRef[ref_id].delete()
        return self  # reload


class ArticleRef(Object):

    iface = Iface('article_ref')
    view_id = 'article_ref'

    def __init__( self, path, article_id, ref_id ):
        Object.__init__(self, path)
        self.article_id = article_id
        self.ref_id = ref_id

    @classmethod
    def make( cls, article_id, ref_id ):
        path = module.make_path(object='article_ref', article_id=article_id, ref_id=ref_id)
        return cls(path, article_id, ref_id)

    @classmethod
    def from_path( cls, path ):
        article_id = path['article_id']
        ref_id = path['ref_id']
        return cls(path, article_id, ref_id)

    @db_session
    def get_json( self ):
        if self.ref_id is None:
            ref_path = None
        else:
            rec = module.ArticleRef[self.ref_id]
            ref_path = rec.path
        return dict(
            Object.get_json(self),
            ref_path=ref_path)

    def get_commands( self ):
        return [Command('save', 'Save', 'Save edited path', 'Ctrl+S')]

    def run_command( self, command_id, request ):
        if command_id == 'save':
            return self.run_command_save(request)
        assert False, repr(command_id)  # Unsupported command

    def run_command_save( self, request ):
        ref_path = request['ref_path']
        with db_session:
            if self.ref_id is None:
                rec = module.ArticleRef(article=module.Article[self.article_id],
                                        path=ref_path)
            else:
                rec = module.ArticleRef[self.ref_id]
                rec.path = ref_path
        print 'Saved article#%d reference#%d path: %r' % (rec.article.id, rec.id, rec.path)
        return dict(self.path, ref_id=rec.id)


class RefSelector(Object):

    iface = Iface('object_selector')
    view_id = 'object_selector'

    def __init__( self, path, article_id, ref_id ):
        Object.__init__(self, path)
        self.article_id = article_id
        self.ref_id = ref_id

    @classmethod
    def make( cls, article_id, ref_id ):
        path = module.make_path(object='article_ref_selector', article_id=article_id, ref_id=ref_id)
        return cls(path, article_id, ref_id)

    @classmethod
    def from_path( cls, path ):
        article_id = path['article_id']
        ref_id = path['ref_id']
        return cls(path, article_id, ref_id)

    @db_session
    def get_json( self ):
        if self.ref_id is None:
            target = None
        else:
            rec = module.ArticleRef[self.ref_id]
            target_path = json.loads(rec.path)
            target = module.get_object(target_path)
        return dict(
            Object.get_json(self),
            target=target.iface.get(target) if target else None)
    

class ArticleModule(PonyOrmModule):

    def __init__( self ):
        PonyOrmModule.__init__(self, MODULE_NAME)
        self.article_fields = dict(text=Required(unicode),
                                   refs=Set('ArticleRef'))

    def init_phase2( self ):
        self.Article = self.make_entity('Article', **self.article_fields)
        self.ArticleRef = self.make_entity('ArticleRef',
                                           article=Required(self.Article),
                                           path=Optional(str),
                                           )

    def resolve( self, path ):
        objname = path['object']
        if objname == 'article':
            return Article.from_path(path)
        if objname == 'article_ref_list':
            return ArticleRefList.from_path(path)
        if objname == 'article_ref':
            return ArticleRef.from_path(path)
        if objname == 'article_ref_selector':
            return RefSelector.from_path(path)
        return PonyOrmModule.resolve(self, path)

    def get_commands( self ):
        return [ModuleCommand('create', 'Create article', 'Create new article', 'Alt+A', self.name)]

    def run_command( self, command_id ):
        if command_id == 'create':
            return Article.from_path(self.make_path(object='article', article_id=None))
        assert False, repr(command_id)  # Unsupported command

    def add_article_fields( self, **fields ):
        self.article_fields.update(fields)


module = ArticleModule()
