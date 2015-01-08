from datetime import datetime
from pony.orm import db_session, Required, Set
from ponyorm_module import PonyOrmModule
from module import ModuleCommand
import article


MODULE_NAME = 'blog'


class BlogEntry(article.Article):

    pass


class BlogModule(PonyOrmModule):

    def __init__( self ):
        PonyOrmModule.__init__(self, MODULE_NAME)
        self.article_module = article.module
        self.article_module.add_article_fields(blog=Set('Blog'))

    def init_phase2( self ):
        self.Article = self.article_module.Article
        self.Blog = self.make_entity('Blog',
                                     article=Required(self.Article),
                                     created_at=Required(datetime))

    def get_commands( self ):
        return [ModuleCommand('create', 'Create entry', 'Create new blog entry', 'Alt+B', self.name)]

    def run_command( self, command_id ):
        if command_id == 'create':
            return BlogEntry()
        assert False, repr(command_id)  # Unsupported command


module = BlogModule()
