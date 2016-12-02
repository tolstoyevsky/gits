#!/usr/bin/env python3
# Copyright 2015 Evgeny Golyshev
# All Rights Reserved.
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
import optparse
import os
import pty
import signal
import socket  # only for gethostname()
import struct
import sys
import termios

import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.websocket import WebSocketHandler

import terminal

os.chdir(os.path.normpath(os.path.dirname(__file__)))


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.htm")


class BasicHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("basic.htm")


class ControlPanelHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("control-panel.htm")


class TermSocketHandler(WebSocketHandler):
    clients = {}

    def __init__(self, application, request, **kwargs):
        WebSocketHandler.__init__(self, application, request, **kwargs)

        self.fd = None
        self._io_loop = tornado.ioloop.IOLoop.current()

    def create(self, rows=24, cols=80):
        pid, fd = pty.fork()
        if pid == 0:
            if os.getuid() == 0:
                cmd = ['/bin/login']
            else:
                # В Python 3.x, в отличии от Python 2.x, для того чтобы строка
                # попала в Терминал, необходимо завершить ее символом \n,
                # который в данном случае эмулирует нажатие клавиши Enter.
                # Однако, необходимость вводить таким образом логин при
                # подключении к машине через ssh является всего лишь временной
                # мерой. В недалеком будущем Терминал будет расширен опцией
                # командной строки, которая позволит указать как логин, так и
                # хост. К примеру, --ssh eugulixes@192.168.0.100.
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
                "client": self,
                "pid": pid,
                "terminal": terminal.Terminal(rows, cols)
            }

            return fd

    def open(self):
        def callback(*args, **kwargs):
            buf = os.read(self.fd, 65536)
            TermSocketHandler.clients[self.fd]['terminal'].write(buf)
            dump = TermSocketHandler.clients[self.fd]['terminal'].dumphtml()
            TermSocketHandler.clients[self.fd]['client'].write_message(dump)

        self.fd = self.create()
        self._io_loop.add_handler(self.fd, callback, self._io_loop.READ)

    def on_message(self, request):
        label, data = request.split(',')

        if label == 'key':
            try:
                os.write(self.fd, data.encode("utf8"))
            except (IOError, OSError):
                self.kill(self.fd)
        elif label == 'rsz':
            row, col = data.split('x')
            fcntl.ioctl(self.fd,
                        termios.TIOCSWINSZ,
                        struct.pack("HHHH", int(row), int(col), 0, 0))
            self.clients[self.fd]["terminal"].set_resolution(int(row), int(col))

    def on_close(self):
        self._io_loop.remove_handler(self.fd)
        self.kill(self.fd)

    def kill(self, fd):
        try:
            os.close(fd)
            os.kill(self.clients[fd]["pid"], signal.SIGHUP)
        except (IOError, OSError):
            pass
        del self.clients[fd]


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", IndexHandler),
            (r"/basic", BasicHandler),
            (r"/control-panel", ControlPanelHandler),
            (r"/termsocket", TermSocketHandler),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
        )
        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-p", "--port", default=8888,
                      help="the port on which the web server is listening")

    (options, args) = parser.parse_args()

    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
