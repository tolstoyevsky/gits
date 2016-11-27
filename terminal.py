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

import array
import codecs
import html
import re

# XXX: Есть один баг. Для воспроизведения необходимо выполнить в домашней
# директории ls | less, а затем сделать поиск по new books. Программа
# выволится с исключением KeyError: '\x1bMmm\r'. mm -- это директория перед
# new books.


class Terminal:
    def __init__(self, rows=24, cols=80):
        self._cols = cols
        self._rows = rows
        self._cur_y = None
        self._cur_x = None
        # The following two fields are used only for implementation of
        # storing (sc) and restoring (rc) the current cursor position.
        self._cur_x_bak = 0
        self._cur_y_bak = 0
        self._screen = None

        self.control_characters = {
            "\x00": None,
            "\x05": self.esc_da,  # ENQ, Ctrl-E
            "\x07": self.esc_ignore,
            "\x08": self.esc_0x08,  # BS, Ctrl-H
            "\x09": self.esc_0x09,  # HT. Ctrl-I
            "\x0a": self.esc_0x0a,  # LF, Ctrl-J
            "\x0b": self.esc_0x0a,  # VT, Ctrl-K
            "\x0c": self.esc_0x0a,  # FF, Ctrl-L
            "\x0d": self.esc_0x0d,  # CR, Ctrl-M
            # "\x0e": None,
            # "\x0f": None,
        }
        self.decoder = codecs.getincrementaldecoder('utf8')()
        self.esc_re = []
        self.new_sci_seq = {
            '\x1b7': 'sc',
            '\x1b8': 'rc',
            '\x1b[@': 'ich1',
            '\x1b[4h': 'smir',
            '\x1b[4l': 'rmir',

            # такой управляющей последовательности нет, но это не мешает,
            # к примеру, ls слать ее
            '\x1b[0m': 'noname',
            '\x1b[1m': 'bold',
            '\x1b[2m': 'dim',
            '\x1b[4m': 'smul',
            '\x1b[5m': 'blink',
            '\x1b[7m': 'smso_rev',
            '\x1b[10m': 'rmpch',
            '\x1b[11m': 'smpch',
            '\x1b[24m': 'rmul',
            '\x1b[27m': 'rmso',
            '\x1b[0;10m': 'sgr0',
            '\x1b[39;49m': 'op',
            '\x1b[A': 'kcuu1',
            '\x1b[B': 'kcud1',
            '\x1b[C': 'kcuf1',  # cuf1
            '\x1b[D': 'kcub1',
            '\x1b[G': 'kb2',
            '\x1b[H': 'home',
            '\x1b[J': 'ed',
            '\x1b[K': 'el',
            '\x1b[1K': 'el1',
            '\x1b[L': 'il1',
            '\x1b[M': 'dl1',
            '\x1b[P': 'dch1',

            # '\x1b[?25l': 'civis',
            # '\x1b[?25h\x1b[?8c': 'cvvis',
        }
        self.new_sci_seq_re = {
            '\x1b[%dd': 'vpa',
            '\x1b[%d;%dm': 'set_colour_pair',  # custom
            '\x1b[%dm': 'set_colour',  # custom
            '\x1b[%dC': 'cuf',
            '\x1b[%dL': 'il',
            '\x1b[%dM': 'dl',
            '\x1b[%dP': 'dch',
            '\x1b[%dX': 'ech',
            '\x1b[%d;%dr': 'csr',
            '\x1b[%d;%dH': 'cup',
        }
        self.new_sci_seq_re_compiled = []
        self.csi_seq = {
            '`': (self.cap_kb2, [1]),
            # 'A': (self.csi_A, [1]),
            # 'B': (self.csi_B, [1]),
            # 'C': (self.csi_C, [1]),
            # 'D': (self.csi_D, [1]),
            # 'G': (self.csi_G, [1]),  # hpa: ESC [ %d G
            # 'H': (self.csi_H, [1]),  # cup: ESC [ %d ; %d H
            # 'J': (self.csi_J, [0]),
            # 'K': (self.csi_K, [0]),
            # Две следующие последовательности не встречаются ни в mc, ни в
            # htop, ни в vim
            # 'L': (self.csi_L, [1]),
            # 'M': (self.csi_M, [1]),
            # 'P': (self.csi_P, [1]),  # dch: ESC [ %d P
            # 'X': (self.csi_X, [1]),  # _only_ ech: ESC [ %d X
            # представляет собой вторую часть последовательностей
            # \x1b[?25l\x1b[?1c и \x1b[?25h\x1b[?8c, поэтому она игнорируется,
            # т.к. является бесполезной без своей первой части
            # 'c': (self.csi_c, [1]),
            # 'd': (self.csi_d, [1]),  # _only_ vpa: ESC [ %d d
            # 'h': (self.csi_h, [1]),  # _only_ smir: ESC [ 4 h
            # 'l': (self.csi_l, [1]),  # _only_ rmir= ESC [ 4 l
            # 'm': (self.csi_m, [1]),  # blink: ESC [ 5 m
                                       # bold: ESC [ 1 m
                                       # dim: ESC [ 2 m
                                       # op: ESC [ 39 ; 49 m
                                       # rev: ESC [ 7 m
                                       # rmacs: ESC [ 10 m
                                       # rmpch: ESC [ 10 m
                                       # rmso: ESC [ 27 m
                                       # rmul: ESC [ 24 m
                                       # setab: ESC [ 4 %d m
                                       # setaf: ESC [ 3 %d m
                                       # sgr0: ESC [ 0 ; 10 m
            # 'r': (self.csi_r, [1]),  # csr: ESC [ %d; %d r
            # 's': (self.csi_s, [1]),  # TODO: удалить
            # 'u': (self.csi_u, [1]),  # TODO: удалить
        }
        self.init()
        self.reset()
        # self.st = None
        # self.sb = None
        # self.cl = None
        # self.sgr = None
        self.buf = ''
        # self.outbuf = None

    def cap_civis(self):
        pass

    def cap_cvvis(self):
        pass

    def init(self):
        for k, v in list(self.new_sci_seq_re.items()):
            res = k.replace('[', '\[').\
                    replace('%d', '([0-9]+)')
            self.new_sci_seq_re_compiled.append(
                (re.compile(res), v)
            )

        # спотыкнулся об \x1b[?2004l, когда удалил следующие строки;
        # видимо это хороший способ генерировать заглушки для различных
        # несуществующих последовательностей.
        d = {
            r'\[\??([0-9;]*)([@ABCDEFGHJKLMPXacdefghlmnqrstu`])':
                self.csi_dispatch,
            r'\]([^\x07]+)\x07': self.esc_ignore,
        }

        for k, v in list(d.items()):
            self.esc_re.append((re.compile('\x1b' + k), v))

    def reset(self, s=''):
        # Попытка разгадать некоторые «магические числа».
        # Число 0x7000000 (117 440 512) представляет собой умноженное на 7
        # число 16 777 216 (0x1000000), которое, в свою очередь, представляет
        # собой количество уникальных цветов в цветовом пространстве модели
        # RGB.
        self._screen = array.array('L',
                                   [0x07000000] * (self._cols * self._rows))
        self.st = 0
        self.sb = self._rows - 1
        self._cur_x_bak = self._cur_x = 0
        self._cur_y_bak = self._cur_y = 0
        self.cl = 0
        self.sgr = 0x07000000
        self.buf = ""
        self.outbuf = ""

    def peek(self, left_border, right_border):
        """

        The name of the method was inherited from AjaxTerm, developers of
        which, in turn, inherited it from BASIC. See poke.
        """
        x1, y1 = left_border
        x2, y2 = right_border
        begin = self._cols * y1 + x1
        end = self._cols * y2 + x2
        return self._screen[begin:end]

    def poke(self, pos, s):
        """

        The name of the method was inherited from AjaxTerm, developers of
        which, in turn, inherited it from BASIC. See peek.
        """
        x, y = pos
        begin = self._cols * y + x
        self._screen[begin:begin + len(s)] = s

    def zero(self, left_border, right_border):
        """Clears the area from the left border ``(x1, y2)`` to the right
        border ``(x2, y2)`` inclusive."""

        x1, y1 = left_border
        x2, y2 = right_border
        begin = self._cols * y1 + x1
        end = self._cols * y2 + x2 + 1
        length = end - begin  # the length of the area which have to be cleared
        self._screen[begin:end] = array.array('L', [0x07000000] * length)
        return length

    def scroll_up(self, y1, y2):
        """Передвигает участок 0,y1 x 0,y2 на одну строку вверх,
        где 0 < y1 < y2.
        """
        # y1 + 1 потому, что копирование происходит со следующей строки
        line = self.peek((0, y1 + 1), (self._cols, y2))
        self.poke((0, y1), line)
        self.zero((0, y2), (self._cols - 1, y2))

    def scroll_down(self, y1, y2):
        """Передвигает участок 0,y1 x 0,y2 на одну строку вниз,
        где 0 < y1 < y2.
        """
        line = self.peek((0, y1), (self._cols, y2 - 1))
        self.poke((0, y1 + 1), line)
        self.zero((0, y1), (self._cols - 1, y1))

    def scroll_right(self, y, x):
        self.poke((x + 1, y), self.peek((x, y), (self._cols, y)))
        self.zero((x, y), (x, y))

    def cursor_down(self):
        if self.st <= self._cur_y <= self.sb:
            self.cl = 0
            q, r = divmod(self._cur_y + 1, self.sb + 1)
            if q:
                self.scroll_up(self.st, self.sb)
                self._cur_y = self.sb
            else:
                self._cur_y = r

    def cursor_right(self):
        q, r = divmod(self._cur_x + 1, self._cols)
        if q:
            self.cl = 1
        else:
            self._cur_x = r

    def echo(self, c):
        if self.cl:
            self.cursor_down()
            self._cur_x = 0

        self._screen[(self._cur_y * self._cols) + self._cur_x] = self.sgr | ord(c)
        self.cursor_right()

    def csi_dispatch(self, seq, mo):
        # CSI sequences
        s = mo.group(1)
        c = mo.group(2)
        f = self.csi_seq.get(c, None)
        if f:
            try:
                l = [min(int(i), 1024) for i in s.split(';') if len(i) < 4]
            except ValueError:
                l = []

            if len(l) == 0:
                l = f[1]

            f[0](l)

    def csi_at(self, l):
        for i in range(l[0]):
            self.cap_ich1()

    # def csi_E(self, l):
    #     self.csi_B(l)
    #     self._cur_x = 0
    #     self.cl = 0

    # def csi_F(self, l):
    #     self.csi_A(l)
    #     self._cur_x = 0
    #     self.cl = 0

    # def csi_a(self, l):
    #     self.csi_C(l)

    # def csi_c(self, l):
    #     # '\x1b[?0c' 0-8 cursor size
    #     pass

    # def csi_e(self, l):
    #     self.csi_B(l)

    # def csi_f(self, l):
    #     self.csi_H(l)

    # новый стиль именования методов, реализующих возможности

    def esc_0x08(self, s):
        self._cur_x = max(0, self._cur_x - 1)

    def esc_0x09(self, s):
        x = self._cur_x + 8
        q, r = divmod(x, 8)
        self._cur_x = (q * 8) % self._cols

    def esc_0x0a(self, s):
        self.cursor_down()

    def esc_0x0d(self, s):
        self.cl = 0
        self._cur_x = 0

    def esc_da(self, s):
        self.outbuf = "\x1b[?6c"

    def esc_ri(self, s):
        self._cur_y = max(self.st, self._cur_y - 1)
        if self._cur_y == self.st:
            self.scroll_down(self.st, self.sb)

    def esc_ignore(self, *s):
        pass

    def cap_set_colour_pair(self, mo=None, p1=None, p2=None):
        if mo:
            p1 = int(mo.group(1))
            p2 = int(mo.group(2))

        if p1 == 0 and p2 == 10:  # sgr0
            self.sgr = 0x07000000
        elif p1 == 39 and p2 == 49:  # op
            self.sgr = 0x07000000
        else:
            self.cap_set_colour(colour=p1)
            self.cap_set_colour(colour=p2)

    def cap_set_colour(self, mo=None, colour=None):
        if mo:
            colour = int(mo.group(1))

        if colour == 0:
            self.sgr = 0x07000000
        elif colour == 1:  # bold
            self.sgr = (self.sgr | 0x08000000)
        elif colour == 2:  # dim
            pass
        elif colour == 4:  # smul
            pass
        elif colour == 5:  # blink
            pass
        elif colour == 7:  # smso or rev
            self.sgr = 0x70000000
        elif colour == 10:  # rmpch
            pass
        elif colour == 11:  # smpch
            pass
        elif colour == 24:  # rmul
            pass
        elif colour == 27:  # rmso
            self.sgr = 0x07000000
        elif 30 <= colour <= 37:  # 7 или 8 цветов
            c = colour - 30
            self.sgr = (self.sgr & 0xf8ffffff) | (c << 24)
        elif colour == 39:
            self.sgr = 0x07000000
        elif 40 <= colour <= 47:
            c = colour - 40
            self.sgr = (self.sgr & 0x0fffffff) | (c << 28)
        elif colour == 49:
            self.sgr = 0x07000000

    def cap_sgr0(self, mo=None, p1=''):
        self.cap_set_colour_pair(p1=0, p2=10)

    def cap_op(self, mo=None, p1=''):
        self.cap_set_colour_pair(p1=39, p2=49)

    def cap_noname(self, p1=''):
        self.cap_set_colour(colour=0)

    def cap_bold(self, p1=''):
        self.cap_set_colour(colour=1)

    def cap_dim(self, p1=''):
        self.cap_set_colour(colour=2)

    def cap_smul(self, p1=''):
        self.cap_set_colour(colour=4)

    def cap_blink(self, p1=''):
        self.cap_set_colour(colour=5)

    def cap_smso_rev(self, p1=''):
        self.cap_set_colour(colour=7)

    def cap_rmpch(self, p1=''):
        self.cap_set_colour(colour=10)

    def cap_smpch(self, p1=''):
        self.cap_set_colour(colour=11)

    def cap_rmul(self, p1=''):
        self.cap_set_colour(colour=24)

    def cap_rmso(self, p1=''):
        self.cap_set_colour(colour=27)

    def cap_sc(self, s=''):
        """Save cursor position """
        self._cur_x_bak = self._cur_x
        self._cur_y_bak = self._cur_y

    def cap_rc(self, s=''):
        """Restore cursor to position of last sc """
        self._cur_x = self._cur_x_bak
        self._cur_y = self._cur_y_bak
        self.cl = 0

    def cap_ich1(self, l=[1]):
        """Insert character """
        self.scroll_right(self._cur_y, self._cur_x)

    def cap_smir(self, l=''):
        """Insert mode (enter) """
        pass

    def cap_rmir(self, l=''):
        """End insert mode """
        pass

    def cap_smso(self, l=''):
        """Begin standout mode """
        self.sgr = 0x70000000

    def cap_kcuu1(self, l=[1]):
        """sent by terminal up-arrow key """
        self._cur_y = max(self.st, self._cur_y - l[0])

    def cap_kcud1(self, l=[1]):
        """sent by terminal down-arrow key """
        self._cur_y = min(self.sb, self._cur_y + l[0])

    def cap_kcuf1(self, l=[1]):
        """sent by terminal right-arrow key """
        self.cap_cuf(p1=0)

    def cap_cuf(self, mo=None, p1=None):
        if mo:
            p1 = int(mo.group(1))

        self._cur_x = min(self._cols - 1, self._cur_x + p1)
        self.cl = 0

    def cap_kcub1(self, l=[1]):
        """sent by terminal left-arrow key """
        self._cur_x = max(0, self._cur_x - l[0])
        self.cl = 0

    def cap_kb2(self, l=[1]):
        """center of keypad """
        self._cur_x = min(self._cols, l[0]) - 1

    def cap_home(self, l=[1, 1]):
        """Home cursor """
        self._cur_x = min(self._cols, l[1]) - 1
        self._cur_y = min(self._rows, l[0]) - 1
        self.cl = 0

    def cap_ed(self, l=[0]):
        """Clear to end of display """
        if l[0] == 0:
            self.zero((self._cur_x, self._cur_y),
                      (self._cols - 1, self._rows - 1))
        elif l[0] == 1:
            self.zero((0, 0), (self._cur_x, self._cur_y))
        elif l[0] == 2:
            self.zero((0, 0), (self._cols - 1, self._rows - 1))

    def cap_el(self, l=[0]):
        """Clear to end of line """
        if l[0] == 0:
            self.zero((self._cur_x, self._cur_y),
                      (self._cols - 1, self._cur_y))
        elif l[0] == 1:
            self.zero((0, self._cur_y), (self._cur_x, self._cur_y))
        elif l[0] == 2:
            self.zero((0, self._cur_y), (self._cols - 1, self._cur_y))

    def cap_el1(self, l=[0]):
        self.cap_el([1])

    def cap_il1(self, l=''):
        """Add new blank line """
        self.cap_il(p1=1)

    def cap_dl1(self, l=''):
        """Delete line """
        self.cap_dl(p1=1)

    def cap_dch1(self, l=''):
        """Delete character """
        self.cap_dch(1)

    def cap_vpa(self, mo):
        """Set vertical position to absolute #1 """
        p = int(mo.group(1))
        self._cur_y = min(self._rows, p) - 1

    def cap_il(self, mo=None, p1=None):
        """Add #1 new blank lines """
        if mo:
            tmp = mo.group(1)
            p1 = int(mo.group(1))

        for i in range(p1):
            if self._cur_y < self.sb:
                self.scroll_down(self._cur_y, self.sb)

    def cap_dl(self, mo=None, p1=None):
        """Delete #1 lines """
        if mo:
            p1 = int(mo.group(1))

        if self.st <= self._cur_y <= self.sb:
            for i in range(p1):
                self.scroll_up(self._cur_y, self.sb)

    def cap_dch(self, mo=None, p1=None):
        """Delete #1 chars """
        if mo:
            p1 = int(mo.group(1))

        w, cx, cy = self._cols, self._cur_x, self._cur_y
        end = self.peek((cx, cy), (w, cy))
        self.cap_el([0])
        self.poke((cx, cy), end[p1:])

    def cap_csr(self, mo):
        """Change to lines #1 through #2 (VT100) """
        p1 = int(mo.group(1))
        p2 = int(mo.group(2))
        self.st = min(self._rows - 1, p1 - 1)
        self.sb = min(self._rows - 1, p2 - 1)
        self.sb = max(self.st, self.sb)

    def cap_ech(self, mo):
        """Erase #1 characters """
        p = int(mo.group(1))
        self.zero((self._cur_x, self._cur_y), (self._cur_x + p, self._cur_y))

    def cap_cup(self, mo):
        """Move to row #1 col #2 """
        p1 = int(mo.group(1))
        p2 = int(mo.group(2))
        self._cur_x = min(self._cols, p2) - 1
        self._cur_y = min(self._rows, p1) - 1
        self.cl = 0

    def exec_escape_sequence(self):
        e = self.buf

        if e == '\x1b[?2004l':
            pass

        method_name = self.new_sci_seq.get(self.buf, None)

        if len(e) > 32:
            self.buf = ''
        elif method_name:  # т.н. статические последовательности
            method = getattr(self, 'cap_' + method_name)
            method()
            self.buf = ''
        else:  # последовательности с параметрами
            for k, v in self.new_sci_seq_re_compiled:
                mo = k.match(e)
                if mo:
                    method = getattr(self, 'cap_' + v)
                    method(mo)
                    e = ''
                    self.buf = ''

            for r, f in self.esc_re:
                mo = r.match(e)
                if mo:
                    f(e, mo)
                    self.buf = ''
                    break

    def exec_single_character_command(self):
        self.control_characters[self.buf](self.buf)
        self.buf = ''

    def write(self, s):
        for i in self.decoder.decode(s):
            if i in self.control_characters:
                self.buf += i
                self.exec_single_character_command()
            elif i == '\x1b':
                self.buf += i
            elif len(self.buf):
                self.buf += i
                self.exec_escape_sequence()
            else:
                self.echo(i)

    def dumphtml(self):
        h = self._rows
        w = self._cols
        r = ''

        # Строка, содержащая готовый к выводу символ.
        span = ''
        span_bg, span_fg = -1, -1
        for i in range(h * w):
            q, c = divmod(self._screen[i], 256 * 256 * 256)
            bg, fg = divmod(q, 16)

            # AjaxTerm использует черный цвет в качестве фона для терминала,
            # не имея при этом опции, которая позволяет его изменить. Таким
            # образом, если AjaxTerm получит предложение об отображении экрана,
            # содержащего _насыщенные_ цвета, он откорректирует это
            # предложение, заменив каждый такой цвет на его _обычный_ аналог.
            #
            # Имея, к примеру, насыщенный зеленый цвет (номер 10), посредством
            # побитового И, можно получить его обычный аналог, т.е. номер 2.
            bg &= 0x7

            if i == self._cur_y * w + self._cur_x:
                bg, fg = 1, 7

            # Если характеристики текущей ячейки совпадают с характеристиками
            # предыдущей (или предыдущих), то объединить их в группу.
            #
            # XXX: терминал не отображает последний символ в правом нижнем углу
            # (особенно это заметно при работе с Midnight Commander).
            if bg != span_bg or fg != span_fg or i + 1 == h * w:
                if len(span):
                    # Заменить каждый пробел на неразрывный пробел
                    # (non-breaking space).
                    ch = span.replace(' ', '\xa0')
                    r += '<span class="f{} b{}">{}</span>'.format(
                        span_fg,
                        span_bg,
                        html.escape(ch)
                    )
                span = ''
                span_bg, span_fg = bg, fg

            if c == 0:
                span += ' '

            span += chr(c & 0xFFFF)

            if not (i + 1) % w:
                span += '\n'

        return r

    def set_resolution(self, row, col):
        self._rows = row
        self._cols = col
        self.reset()
