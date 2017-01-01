#!/usr/bin/env python3
# Copyright 2013-2016 Evgeny Golyshev <eugulixes@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import fcntl
import os
import pty
import signal
import socket  # only for gethostname()
import struct
import sys
import termios

import tornado.httpserver
import tornado.options
import tornado.web
from tornado.ioloop import IOLoop
from tornado.options import define, options
from tornado.websocket import WebSocketHandler

from gits.terminal import Terminal

define('port', help='listen on a specific port', default=8888)
define('static_path', help='the path to static resources',
       default=os.path.join(os.getcwd(), 'node_modules/gits-client/static'))
define('templates_path', help='the path to templates',
       default=os.path.join(os.getcwd(), 'node_modules/gits-client/templates'))


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.htm')


class TermSocketHandler(WebSocketHandler):
    clients = {}

    def __init__(self, application, request, **kwargs):
        WebSocketHandler.__init__(self, application, request, **kwargs)

        self._fd = None
        self._io_loop = IOLoop.current()

    def _create(self, rows=24, cols=80):
        pid, fd = pty.fork()
        if pid == 0:
            if os.getuid() == 0:
                cmd = ['/bin/login']
            else:
                # The prompt has to end with a newline character.
                sys.stdout.write(socket.gethostname() + ' login: \n')
                login = sys.stdin.readline().strip()

                cmd = [
                    'ssh',
                    '-oPreferredAuthentications=keyboard-interactive,password',
                    '-oNoHostAuthenticationForLocalhost=yes',
                    '-oLogLevel=FATAL',
                    '-F/dev/null',
                    '-l', login, 'localhost',
                ]

            env = {
                'COLUMNS': str(cols),
                'LINES': str(rows),
                'PATH': os.environ['PATH'],
                'TERM': 'linux',
            }
            os.execvpe(cmd[0], cmd, env)
        else:
            fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
            fcntl.ioctl(fd, termios.TIOCSWINSZ,
                        struct.pack('HHHH', rows, cols, 0, 0))
            TermSocketHandler.clients[fd] = {
                'client': self,
                'pid': pid,
                'terminal': Terminal(rows, cols)
            }

            return fd

    def _destroy(self, fd):
        try:
            os.kill(TermSocketHandler.clients[fd]['pid'], signal.SIGHUP)
            os.close(fd)
        except OSError:
            pass

        del TermSocketHandler.clients[fd]

    # Implementing the methods inherited from
    # tornado.websocket.WebSocketHandler

    def open(self):
        def callback(*args, **kwargs):
            buf = os.read(self._fd, 65536)
            TermSocketHandler.clients[self._fd]['terminal'].write(buf)
            dump = TermSocketHandler.clients[self._fd]['terminal'].dumphtml()
            TermSocketHandler.clients[self._fd]['client'].write_message(dump)

        self._fd = self._create()
        self._io_loop.add_handler(self._fd, callback, self._io_loop.READ)

    def on_message(self, data):
        try:
            os.write(self._fd, data.encode('utf8'))
        except (IOError, OSError):
            self._destroy(self._fd)

    def on_close(self):
        self._io_loop.remove_handler(self._fd)
        self._destroy(self._fd)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', IndexHandler),
            (r'/termsocket', TermSocketHandler),
        ]
        settings = dict(
            template_path=options.templates_path,
            static_path=options.static_path,
        )
        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    tornado.options.parse_command_line()

    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    IOLoop.instance().start()

if __name__ == "__main__":
    main()
