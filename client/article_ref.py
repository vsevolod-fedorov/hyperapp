from PySide import QtCore, QtGui
from util import uni2str
from iface import ObjectIface
import iface_registry
import view
import view_registry


class ArticleRef(ObjectIface):

    def __init__( self, server, response ):
        ObjectIface.__init__(self, server, response)
        self.article_id = response['article_id']
        self.ref_path = response['ref_path']

    def path_changed( self, ref_path ):
        self.ref_path = ref_path

    def run_command( self, command_id ):
        if command_id == 'save':
            return self.run_command_save()
        return ObjectIface.run_command(self, command_id)

    def run_command_save( self ):
        request = dict(self.make_command_request(command_id='save'),
                       ref_path=self.ref_path)
        response = self.server.execute_request(request)
        self.path = response['new_path']


class Handle(view.Handle):

    def __init__( self, object, ref_path=None ):
        view.Handle.__init__(self)
        self.object = object
        self.ref_path = ref_path

    def get_title( self ):
        return self.object.get_title()

    def construct( self, parent ):
        print 'article_ref construct', parent, self.object.get_title(), repr(self.ref_path)
        return View(parent, self.object, self.ref_path)

    def __repr__( self ):
        return 'text_edit.Handle(%s, %s)' % (uni2str(self.object.get_title()), uni2str(self.ref_path))


class View(view.View, QtGui.QWidget):

    def __init__( self, parent, object, ref_path ):
        QtGui.QWidget.__init__(self)
        view.View.__init__(self, parent)
        self.object = object
        self.article_id_label = QtGui.QLabel('Article#%d' % self.object.article_id)
        self.path_line_edit = QtGui.QLineEdit()
        self.path_line_edit.textChanged.connect(self._on_path_text_changed)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.article_id_label)
        layout.addWidget(self.path_line_edit)
        self.setLayout(layout)

    def handle( self ):
        return Handle(self.object, '')

    def get_title( self ):
        return self.object.get_title()

    def get_object( self ):
        return self.object

    def get_widget_to_focus( self ):
        return self.path_line_edit

    def _on_path_text_changed( self, text ):
        self.object.path_changed(text)


iface_registry.register_iface('article_ref', ArticleRef)
view_registry.register_view('article_ref', Handle)
