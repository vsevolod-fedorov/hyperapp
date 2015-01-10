#!/usr/bin/env python

import sys
import os
import os.path
import traceback
import re

sys.path.append('..')

import json_connection
from module import Module
import ponyorm_module
import fs
import file_view
import article
import blog


LISTEN_PORT = 8888


class Server(object):

    def __init__( self ):
        Module.init_phases()

    def resolve( self, path ):
        return Module.get_object(path)
        if path.startswith('/article/'):
            return article.Article(path)
        if re.match(r'/blog_entry/\d+/refs$', path):
            return article.ArticleRefList(path)
        if re.match(r'/blog_entry/\d+/refs/[^/]+$', path):
            return article.ArticleRef(path)
        if re.match(r'/blog_entry/\d+/refs/[^/]+/select$', path):
            return article.RefSelector(path)
        if path.startswith('/blog_entry/'):
            return blog.BlogEntry(path)
        if path.startswith('/blog/'):
            return blog.Blog(path)

    def get_object( self, object ):
        if object is None: return None
        iface = object.iface
        return iface.get(object)

    def process_request( self, request ):
        method = request['method']
        # server-global commands
        if method == 'get_commands':
            return self.process_get_commands(request)
        if method == 'run_module_command':
            return self.process_run_module_command(request)
        # object commands
        path = request['path']
        object = self.resolve(path)
        print 'Object:', object
        assert object, repr(path)  # 404: Path not found
        iface = object.iface
        return iface.process_request(object, method, request)

    def process_get_commands( self, request ):
        commands = [cmd.as_json() for cmd in Module.get_all_modules_commands()]
        return dict(commands=commands)

    def process_run_module_command( self, request ):
        module_name = request['module_name']
        command_id = request['command_id']
        obj = Module.run_module_command(module_name, command_id)
        return self.get_object(obj)

    def run( self, connection, cln_addr ):
        print 'accepted connection from %s:%d' % cln_addr
        try:
            while True:
                request = connection.receive()
                print 'request: %r' % request
                try:
                    response = self.process_request(request)
                except:
                    traceback.print_exc()
                    response = dict(error='Internal server error')
                connection.send(response)
        except json_connection.Error as x:
            print x
        except:
            traceback.print_exc()
            


def main():
    server = Server()
    json_server = json_connection.Server(LISTEN_PORT, server.run)
    json_server.run()


main()
