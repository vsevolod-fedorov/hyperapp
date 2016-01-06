import weakref
import uuid
from ..common.endpoint import Url
from ..common.interface import get_iface
from .request import Request
from .server import RespHandler, Server


class GetRespHandler(RespHandler):

    def __init__( self, view ):
        RespHandler.__init__(self, iface=get_iface, command_id='get')
        self.view_wr = weakref.ref(view)

    def process_response( self, response, server ):
        view = self.view_wr()
        if view:
            view.process_handle_open(response.result, server)


def run_get_request( view, url ):
    assert isinstance(url, Url), repr(url)
    server, path = Server.resolve_url(url)
    command_id = 'get'
    resp_handler = GetRespHandler(view)
    request_id = str(uuid.uuid4())
    request = Request(get_iface, path, 'get', request_id)
    server.execute_request(request, resp_handler)
