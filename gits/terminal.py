# Copyright 2013-2016 Evgeny Golyshev <eugulixes@gmail.com>
# Copyright 2016 Dmitriy Shilin <sdadeveloper@gmail.com>
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
import html
import re
from os import path

import yaml


MAGIC_NUMBER = 0x07000000


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

        # eol stands for 'end of line' and is set to True when the cursor
        # reaches the right side of the screen.
        self._eol = False

        # The following fields allow abstracting from the rows and cols
        # concept.
        self._top_most = None
        self._bottom_most = None
        self._left_most = None
        self._right_most = None

        self._sgr = None  # Select Graphic Rendition

        self._buf = ''
        self._outbuf = ''

        with open(path.join(path.dirname(__file__), 'linux_console.yml')) as f:
            sequences = yaml.load(f.read())

        self.control_characters = sequences['control_characters']

        self.esc_re = []
        self.new_sci_seq = {}
        for k, v in sequences['escape_sequences'].items():
            self.new_sci_seq[k.replace('\\E', '\x1b')] = v

        self.new_sci_seq_re = {}
        for k, v in sequences['escape_sequences_re'].items():
            self.new_sci_seq_re[k.replace('\\E', '\x1b')] = v

        self.new_sci_seq_re_compiled = []
        self.csi_seq = {
            '`': (self._cap_kb2, [1]),
        }
        for k, v in list(self.new_sci_seq_re.items()):
            res = k.replace('[', '\['). \
                replace('%d', '([0-9]+)')
            self.new_sci_seq_re_compiled.append(
                (re.compile(res), v)
            )

        d = {
            r'\[\??([0-9;]*)([@ABCDEFGHJKLMPXacdefghlmnqrstu`])':
                self._cap_ignore,
            r'\]([^\x07]+)\x07': self._cap_ignore,
        }

        for k, v in list(d.items()):
            self.esc_re.append((re.compile('\x1b' + k), v))

        self._cap_rs1()

    #
    # Internal methods.
    #
    def _peek(self, left_border, right_border, inclusively=False):
        """Captures and returns a rectangular region of the screen.

        The ``left_border`` and ``right_border`` arguments must be tuples or
        lists of coordinates ``(x1, y1)`` and ``(x2, y2)``, respectively.

        The name of the method was inherited from AjaxTerm, developers of
        which, in turn, inherited it from BASIC. See _poke.
        """
        x1, y1 = left_border
        x2, y2 = right_border
        begin = self._cols * y1 + x1
        end = self._cols * y2 + x2 + (1 if inclusively else 0)
        return self._screen[begin:end]

    def _poke(self, pos, s):
        """Puts the specified string ``s`` on the screen staring at the
        specified position ``pos``.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.

        The name of the method was inherited from AjaxTerm, developers of
        which, in turn, inherited it from BASIC. See _peek.
        """
        x, y = pos
        begin = self._cols * y + x
        self._screen[begin:begin + len(s)] = s

    def _zero(self, left_border, right_border, inclusively=False):
        """Clears the area from ``left_border`` to ``right_border``.

        The ``left_border`` and ``right_border`` arguments must be tuples or
        lists of coordinates ``(x1, y1)`` and ``(x2, y2)``, respectively.
        """
        x1, y1 = left_border
        x2, y2 = right_border
        begin = self._cols * y1 + x1
        end = self._cols * y2 + x2 + (1 if inclusively else 0)
        length = end - begin  # the length of the area which have to be cleared
        self._screen[begin:end] = array.array('L', [MAGIC_NUMBER] * length)
        return length

    def _scroll_up(self, y1, y2):
        """Moves the area specified by coordinates 0, ``y1`` and 0, ``y2`` up 1
        row.
        """
        area = self._peek((0, y1), (self._right_most, y2), inclusively=True)
        self._poke((0, y1 - 1), area)  # move the area up 1 row (y1 - 1)
        self._zero((0, y2), (self._cols, y2))

    def _scroll_down(self, y1, y2):
        """Moves the area specified by coordinates 0, ``y1`` and 0, ``y2`` down
        1 row.
        """
        line = self._peek((0, y1), (self._cols, y2 - 1))
        self._poke((0, y1 + 1), line)
        self._zero((0, y1), (self._cols, y1))

    def _scroll_right(self, x, y):
        """Moves a piece of a row specified by coordinates ``x`` and ``y``
        right by 1 position.
        """

        self._poke((x + 1, y), self._peek((x, y), (self._cols, y)))
        self._zero((x, y), (x, y), inclusively=True)

    def _cursor_down(self):
        """Moves the cursor down by 1 position. If the cursor reaches the
        bottom of the screen, its content moves up 1 row.
        """
        if self._top_most <= self._cur_y <= self._bottom_most:
            self._eol = False
            q, r = divmod(self._cur_y + 1, self._bottom_most + 1)
            if q:
                self._scroll_up(self._top_most + 1, self._bottom_most)
                self._cur_y = self._bottom_most
            else:
                self._cur_y = r

    def _cursor_right(self):
        """Moves the cursor right by 1 position. """
        q, r = divmod(self._cur_x + 1, self._cols)
        if q:
            self._eol = True
        else:
            self._cur_x = r

    def _echo(self, c):
        """Puts the specified character ``c`` on the screen and moves the
        cursor right by 1 position. If the cursor reaches the end of a line,
        it is moved to the next line.
        """
        if self._eol:
            self._cursor_down()
            self._cur_x = 0

        pos = self._cur_y * self._cols + self._cur_x
        self._screen[pos] = self._sgr | ord(c)
        self._cursor_right()

    def _cap_set_color_pair(self, mo=None, p1=None, p2=None):
        if mo:
            p1 = int(mo.group(1))
            p2 = int(mo.group(2))

        if p1 == 0 and p2 == 10:  # sgr0
            self._sgr = MAGIC_NUMBER
        elif p1 == 39 and p2 == 49:  # op
            self._sgr = MAGIC_NUMBER
        else:
            self._cap_set_color(colour=p1)
            self._cap_set_color(colour=p2)

    def _cap_set_color(self, mo=None, colour=None):
        if mo:
            colour = int(mo.group(1))

        if colour == 0:
            self._sgr = MAGIC_NUMBER
        elif colour == 1:  # bold
            self._sgr = (self._sgr | 0x08000000)
        elif colour == 2:  # dim
            pass
        elif colour == 4:  # smul
            pass
        elif colour == 5:  # blink
            pass
        elif colour == 7:  # smso or rev
            self._sgr = 0x70000000
        elif colour == 10:  # rmpch
            pass
        elif colour == 11:  # smpch
            pass
        elif colour == 24:  # rmul
            pass
        elif colour == 27:  # rmso
            self._sgr = MAGIC_NUMBER
        elif 30 <= colour <= 37:  # setaf
            c = colour - 30
            self._sgr = (self._sgr & 0xf8ffffff) | (c << 24)
        elif colour == 39:
            self._sgr = MAGIC_NUMBER
        elif 40 <= colour <= 47:  # setab
            c = colour - 40
            self._sgr = (self._sgr & 0x0fffffff) | (c << 28)
        elif colour == 49:
            self._sgr = MAGIC_NUMBER

    def _cap_ignore(self, *s):
        pass

    def _cap_blink(self, p1=''):
        """Produces blinking text. """
        self._cap_set_color(colour=5)

    def _cap_bold(self, p1=''):
        """Produces bold text. """
        self._cap_set_color(colour=1)

    def _cap_civis(self):
        """Makes the cursor invisible. See _cap_cvvis. """
        pass

    def _cap_cr(self):
        """Does carriage return. """
        self._eol = False
        self._cur_x = 0

    def _cap_csr(self, mo):
        """Change to lines #1 through #2 (VT100). """
        p1 = int(mo.group(1))
        p2 = int(mo.group(2))
        self._top_most = min(self._rows - 1, p1 - 1)
        self._bottom_most = min(self._rows - 1, p2 - 1)
        self._bottom_most = max(self._top_most, self._bottom_most)

    def _cap_cub1(self):
        """Moves the cursor left by 1 position.

        Usually the method acts as a handler for a Backspace key-press.
        """
        self._cur_x = max(0, self._cur_x - 1)

        if self._cur_x == self._left_most:
            self._cur_x = self._right_most
            self._cur_y = max(0, self._cur_y - 1)
            self._eol = True

    def _cap_cud(self, mo=None, p1=None):
        """Moves the cursor down the specified number of lines. """
        if mo:
            p1 = int(mo.group(1))

        self._cur_y = min(self._bottom_most, self._cur_y + p1)

    def _cap_cuf(self, mo=None, p1=None):
        """Moves the cursor right by a specified number of positions. """
        if mo:
            p1 = int(mo.group(1))

        for _ in range(p1):
            self._cursor_right()

    def _cap_cup(self, mo):
        """Move to row #1 col #2 """
        p1 = int(mo.group(1))
        p2 = int(mo.group(2))
        self._cur_x = min(self._cols, p2) - 1
        self._cur_y = min(self._rows, p1) - 1
        self._eol = False

    def _cap_cvvis(self):
        """Make the cursor visible. See _cap_civis. """
        pass

    # TODO: rework later
    def _esc_da(self):
        self._outbuf = "\x1b[?6c"  # u8

    def _cap_dch(self, mo=None, p1=None):
        """Deletes the specified number of characters. """
        if mo:
            p1 = int(mo.group(1))

        w, cx, cy = self._cols, self._cur_x, self._cur_y
        end = self._peek((cx, cy), (w, cy))
        self._cap_el([0])
        self._poke((cx, cy), end[p1:])

    def _cap_dch1(self, l=''):
        """Deletes a character. """
        self._cap_dch(1)

    def _cap_dim(self, p1=''):
        """Enters Half-bright mode. """
        self._cap_set_color(colour=2)

    def _cap_dl(self, mo=None, p1=None):
        """Deletes the specified number of lines. """
        if mo:
            p1 = int(mo.group(1))

        if self._top_most <= self._cur_y <= self._bottom_most:
            for i in range(p1):
                self._scroll_up(self._cur_y + 1, self._bottom_most)

    def _cap_dl1(self, l=''):
        """Deletes a line. """
        self._cap_dl(p1=1)

    def _cap_ech(self, mo):
        """Erases the specified number of characters. """
        p = int(mo.group(1))
        self._zero((self._cur_x, self._cur_y), (self._cur_x + p, self._cur_y),
                   inclusively=True)

    def _cap_ed(self, l=None):
        """Clears the screen from the current cursor position to the end of the
        screen.
        """
        self._zero((self._cur_x, self._cur_y), (self._cols, self._rows - 1))

    def _cap_el(self, l=None):
        """Clears a line from the cursor position to the end of the line. """
        if l is None:
            l = [0]

        if l[0] == 0:
            self._zero((self._cur_x, self._cur_y), (self._cols, self._cur_y))
        elif l[0] == 1:
            self._zero((0, self._cur_y), (self._cur_x, self._cur_y),
                       inclusively=True)
        elif l[0] == 2:
            self._zero((0, self._cur_y), (self._cols, self._cur_y))

    def _cap_el1(self, l=None):
        """Clears a line from the beginning of the line to the current cursor
        position.
        """
        if l is None:
            l = [1]
        self._cap_el(l)

    def _cap_home(self, l=None):
        """Moves the cursor to the home position. """
        if l is None:
            l = [1, 1]
        self._cur_x = min(self._cols, l[1]) - 1
        self._cur_y = min(self._rows, l[0]) - 1
        self._eol = False

    def _cap_ht(self):
        x = self._cur_x + 8
        q, r = divmod(x, 8)
        self._cur_x = (q * 8) % self._cols

    def _cap_ich(self, mo=None, p1=None):
        """Inserts the specified number of blank characters. """
        if mo:
            p1 = int(mo.group(1))

        for i in range(p1):
            self._scroll_right(self._cur_x + i, self._cur_y)

    def _cap_il(self, mo=None, p1=None):
        """Adds the specified number of new blank lines. """
        if mo:
            tmp = mo.group(1)
            p1 = int(mo.group(1))

        for i in range(p1):
            if self._cur_y < self._bottom_most:
                self._scroll_down(self._cur_y, self._bottom_most)

    def _cap_il1(self, l=''):
        """Adds a new blank line. """
        self._cap_il(p1=1)

    def _cap_ind(self):
        """Scrolls the screen up moving its content down. """
        self._cursor_down()

    def _cap_kb2(self, l=None):
        """Handles a Center key-press on keypad. """
        if l is None:
            l = [1]
        self._cur_x = min(self._cols, l[0]) - 1

    def _cap_kcub1(self, l=None):
        """Handles a Left Arrow key-press. """
        if l is None:
            l = [1]
        self._cur_x = max(0, self._cur_x - l[0])
        self._eol = False

    def _cap_kcud1(self, s=1):
        """Handles a Down Arrow key-press. """
        self._cap_cud(p1=1)

    def _cap_kcuf1(self, s=''):
        """Handles a Right Arrow key-press. """
        self._cap_cuf(p1=1)

    def _cap_kcuu1(self, l=None):
        """Handles a Up Arrow key-press. """
        if l is None:
            l = [1]
        self._cur_y = max(self._top_most, self._cur_y - l[0])

    def _cap_op(self, mo=None, p1=''):
        self._cap_set_color_pair(p1=39, p2=49)

    def _cap_rc(self, s=''):
        """Restores the cursor to the last saved position. See _cap_sc. """
        self._cur_x = self._cur_x_bak
        self._cur_y = self._cur_y_bak
        self._eol = True if self._cur_x == self._right_most else False

    def _cap_ri(self, s=''):
        """Scrolls text down. See _cap_ind. """
        self._cur_y = max(self._top_most, self._cur_y - 1)
        if self._cur_y == self._top_most:
            self._scroll_down(self._top_most, self._bottom_most)

    def _cap_rmir(self, l=''):
        """Exits Insert mode. See _cap_smir. """
        pass

    def _cap_rmpch(self, p1=''):
        """Exits PC character display mode. See _cap_smpch. """
        self._cap_set_color(colour=10)

    def _cap_rmso(self, p1=''):
        """Exits Standout mode. See _cap_smso. """
        self._cap_set_color(colour=27)

    def _cap_rmul(self, p1=''):
        """Exits Underscore mode. See _cap_smul. """
        self._cap_set_color(colour=24)

    def _cap_rs1(self, s=''):
        """Resets terminal completely to sane modes. """
        cells_number = self._cols * self._rows
        self._screen = array.array('L', [MAGIC_NUMBER] * cells_number)
        self._sgr = MAGIC_NUMBER
        self._cur_x_bak = self._cur_x = 0
        self._cur_y_bak = self._cur_y = 0
        self._eol = False
        self._left_most = self._top_most = 0
        self._bottom_most = self._rows - 1
        self._right_most = self._cols - 1

        self._buf = ''
        self._outbuf = ''

    def _cap_sc(self, s=''):
        """Saves the current cursor position. See _cap_rc. """
        self._cur_x_bak = self._cur_x
        self._cur_y_bak = self._cur_y

    def _cap_sgr0(self, mo=None, p1=''):
        self._cap_set_color_pair(p1=0, p2=10)

    def _cap_smir(self, l=''):
        """Enters Insert mode. See _cap_rmir. """
        pass

    def _cap_smso(self, l=''):
        """Enters Standout mode. See _cap_rmso.

        John Strang, in his book Programming with Curses, gives the following
        definition for the term. Standout mode is whatever special highlighting
        the terminal can do, as defined in the terminal's database entry.
        """
        self._sgr = 0x70000000

    def _cap_smso_rev(self, p1=''):
        self._cap_set_color(colour=7)

    def _cap_smul(self, p1=''):
        """Enters Underscore mode. See _cap_rmul. """
        self._cap_set_color(colour=4)

    def _cap_smpch(self, p1=''):
        """Enters PC character display mode. See _cap_rmpch. """
        self._cap_set_color(colour=11)

    def _cap_vpa(self, mo=None):
        """Sets the vertical position to the `mo` value.
        The `mo` paramater has 1-based indexing, need to have 0-based indexing.
        See _cap_hpa.
        """

        p = int(mo.group(1)) - 1
        self._cur_y = min(self._bottom_most, p)

    def _cap_hpa(self, mo=None):
        """Sets the horizontal position to the `mo` value.
        The `mo` paramater has 1-based indexing, need to have 0-based indexing.
        See _cap_vpa.
        """

        p = int(mo.group(1)) - 1
        self._cur_x = min(self._right_most, p)

    def _cap_noname(self, p1=''):
        self._cap_set_color(colour=0)

    def _exec_escape_sequence(self):
        e = self._buf

        if e == '\x1b[?2004l':
            pass

        method_name = self.new_sci_seq.get(self._buf, None)

        if len(e) > 32:
            self._buf = ''
        elif method_name:  # static sequences
            method = getattr(self, '_cap_' + method_name)
            method()
            self._buf = ''
        else:  # sequences with params
            for k, v in self.new_sci_seq_re_compiled:
                mo = k.match(e)
                if mo:
                    method = getattr(self, '_cap_' + v)
                    method(mo)
                    e = ''
                    self._buf = ''

            for r, f in self.esc_re:
                mo = r.match(e)
                if mo:
                    f(e, mo)
                    self._buf = ''
                    break

    def _exec_single_character_command(self):
        method_name = self.control_characters[self._buf]
        method = getattr(self, '_cap_' + method_name)
        method()
        self._buf = ''

    #
    # User visible methods.
    #
    def write(self, s):
        for i in s.decode('utf8', errors='replace'):
            if ord(i) in self.control_characters:
                self._buf = ord(i)
                self._exec_single_character_command()
            elif i == '\x1b':
                self._buf += i
            elif len(self._buf):
                self._buf += i
                self._exec_escape_sequence()
            else:
                self._echo(i)

    def dumphtml(self):
        h = self._rows
        w = self._cols
        r = ''

        span = ''  # ready-to-output character
        span_bg, span_fg = -1, -1
        for i in range(h * w):
            q, c = divmod(self._screen[i], 256 * 256 * 256)
            bg, fg = divmod(q, 16)

            # Gits supports two color schemes: normal and bright. Each color
            # scheme consists of 8 colors for a background and text. The
            # terminal doesn't allow users to switch between them so far.
            # Gits uses the normal color scheme by default.
            #
            # Suppose we have a bright green color (10). Using bitwise AND, we
            # can get a normal green color (2).
            bg &= 0x7

            if i == self._cur_y * w + self._cur_x:
                bg, fg = 1, 7

            # If the characteristics of the current cell match the
            # characteristics of the previous cell, combine them into a group.
            if bg != span_bg or fg != span_fg or i + 1 == h * w:
                if len(span):
                    # Replace spaces with non-breaking space.
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
