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
import logging
import re
from os import path

import yaml

MAGIC_NUMBER = 0x10000000000
# +------------------+--------------------------------------------------------+
# | character (0-31) | 4-byte value represents a character in UTF-8 encoding. |
# +------------------+--------------------------------------------------------+
# | emphasis and     | 1-byte value represents 8 emphasis and modes. Each of  |
# | modes (32-39)    | them is represented by 1 bit.                          |
# |                  | 32) underline                                          |
# |                  | 33) reverse                                            |
# |                  | 34) blink                                              |
# |                  | 35) dim                                                |
# |                  | 36) bold                                               |
# |                  | 37) blank                                              |
# |                  | 38) protect                                            |
# |                  | 39) alternate character set                            |
# +------------------+--------------------------------------------------------+
# | colors (40-46)   | 7-bit value represents both background and foreground  |
# |                  | color. To get them divide the value by 16 via divmod.  |
# |                  | The result will be a tuple (bg, fg).                   |
# +------------------+--------------------------------------------------------+

# The colors section of MAGIC_NUMBER stores 7, i.e. (0, 7) or black and white.
BLACK_AND_WHITE = MAGIC_NUMBER * 7

UNDERLINE_BIT = 32
REVERSE_BIT = 33
BLINK_BIT = 34
BOLD_BIT = 36


class Terminal:
    def __init__(self, rows=24, cols=80):
        self._cols = cols
        self._rows = rows
        self._cur_y = None
        self._cur_x = None
        self._cur_visible = True

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

        # Gits supports two color schemes: normal and bright. Each color scheme
        # consists of 8 colors for a background and text. The terminal doesn't
        # allow users to switch between them so far.
        # The bright color scheme is used by default.
        self._normal_mode = False

        self._logger = logging.getLogger('tornado.application')

        self._buf = ''
        self._outbuf = ''

        with open(path.join(path.dirname(__file__), 'linux_console.yml')) as f:
            sequences = yaml.load(f.read())

        self.control_characters = sequences['control_characters']

        self._escape_sequences = {}
        for k, v in sequences['escape_sequences'].items():
            self._escape_sequences[k.replace('\\E', '\x1b')] = v

        self._escape_sequences_re = []
        for k, v in sequences['escape_sequences_re'].items():
            sequence = k.replace('\\E', '\x1b'). \
                         replace('[', '\['). \
                         replace('%d', '([0-9]+)')

            self._escape_sequences_re.append(
                (re.compile(sequence), v)
            )

        self._cap_rs1()

    #
    # Internal methods.
    #
    def _peek(self, left_border, right_border, inclusively=False):
        """Captures and returns a rectangular region of the screen between
        ``left_border`` and ``right_border``.

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
        """Puts the specified slice ``s`` on the screen staring at the position
        ``pos``.

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
        self._screen[begin:end] = array.array('Q', [BLACK_AND_WHITE] * length)
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

    def _exec_method(self, name, args=None):
        """Tries to find the specified method and, in case the try succeeds,
        executes it.

        The ``name`` argument is a name of the target method. First,
        `_exec_method` tries to find _cap_``name``, then _``name``.
        The ``args`` argument must be a list of arguments to be passed to the
        target method.
        """
        if args is None:
            args = []

        method = (getattr(self, '_cap_' + name, None) or
                  getattr(self, '_' + name, None))
        if method:
            method(*args)
        else:
            self._logger.fatal('The _cap_{name} and _{name} methods do not '
                               'exist'.format(name=name))

    def _ignore(self):
        """Allows ignoring some escape and control sequences. """
        pass

    def _set_bit(self, bit):
        """Sets the specified `_sgr` bit. """
        self._sgr |= 1 << bit

    def _is_bit_set(self, bit, value):
        """Checks if the specified bit is set in the specified value. """
        return bool(value & (1 << bit))

    def _clean_bit(self, bit):
        """Cleans the specified `_sgr` bit. """
        self._sgr &= ~(1 << bit)

    def _default_rendition(self):
        """Cancels the effect of any preceding occurrence of SGR in the data
        stream regardless of the setting of the GRAPHIC RENDITION COMBINATION
        MODE (GRCM). For details, see section 8.3.117, "SGR - SELECT GRAPHIC
        RENDITION," in ECMA-048 at
        http://www.ecma-international.org/publications/standards/Ecma-048.htm.
        """
        self._set_color(0)

    def _set_bg_color(self, color):
        """Sets the background color. """
        color_bits, _ = divmod(self._sgr, MAGIC_NUMBER)
        _, fg = divmod(color_bits, 16)
        new_color_bits = color * 16 + fg
        self._sgr &= ~(color_bits << 40)  # clear color bits
        self._sgr |= new_color_bits << 40  # update bg and fg colors

    def _set_fg_color(self, color):
        """Sets the foreground color. """
        color_bits, _ = divmod(self._sgr, MAGIC_NUMBER)
        bg, _ = divmod(color_bits, 16)

        # bold also means extra bright, so if the corresponding bit is set, we
        # have to switch to the bright color scheme.
        if self._sgr & (1 << BOLD_BIT):
            color += 8

        new_color_bits = bg * 16 + color
        self._sgr &= ~(color_bits << 40)  # clear color bits
        self._sgr |= new_color_bits << 40  # update bg and fg colors

    def _set_color_pair(self, p1, p2):
        if p1 == 0 and p2 == 10:  # sgr0
            self._sgr = BLACK_AND_WHITE
        elif p1 == 39 and p2 == 49:  # op
            self._sgr = BLACK_AND_WHITE
        else:
            self._set_attribute(p1)
            self._set_color(p2)

    def _set_attribute(self, p1):
        """Sets attribute parameters of SGR. """
        if p1 == 1:
            self._cap_bold()
        elif p1 == 2:
            self._cap_dim()
        elif p1 == 4:
            self._cap_smul()
        elif p1 == 5:
            self._cap_blink()
        elif p1 == 7:
            self._cap_rev()
        elif p1 == 10:
            self._cap_rmpch()
        elif p1 == 11:
            self._cap_smpch()
        elif p1 == 24:
            self._cap_rmul()
        elif p1 == 27:
            self._cap_rmso()

    def _set_color(self, color):
        if color == 0:
            self._sgr = BLACK_AND_WHITE
        elif 30 <= color <= 37:  # setaf
            self._set_fg_color(color - 30)
        elif color == 39:
            self._sgr = BLACK_AND_WHITE
        elif 40 <= color <= 47:  # setab
            self._set_bg_color(color - 40)
        elif color == 49:
            self._sgr = BLACK_AND_WHITE

    def _cap_blink(self):
        """Produces blinking text. """
        self._set_bit(BLINK_BIT)

    def _cap_bold(self):
        """Produces bold text. """
        self._set_bit(BOLD_BIT)
        self._set_color(37)

    def _cap_civis(self):
        """Makes the cursor invisible. See _cap_cvvis. """
        self._cur_visible = False

    def _cap_cr(self):
        """Does carriage return. """
        self._eol = False
        self._cur_x = 0

    def _cap_csr(self, top, bottom):
        """Changes the scrolling region.

        The ``top`` and ``bottom`` parameters are lines of the scrolling
        region. After executing the method, the cursor position is undefined.
        See _cap_sc and _cap_rc.

        The ``top`` and ``bottom`` values start from 1.
        """
        self._top_most = min(self._bottom_most, top - 1)
        self._bottom_most = min(self._bottom_most, bottom - 1)

        # `_bottom_most` must be greater than or equal to `_top_most`.
        self._bottom_most = max(self._top_most, self._bottom_most)

    def _cap_cub1(self):
        """Moves the cursor left by 1 position.

        Usually the method acts as a handler for a Backspace key-press.
        """
        self._cur_x = max(0, self._cur_x - 1)

    def _cap_cud(self, n):
        """Moves the cursor down ``n`` number of lines. """
        self._cur_y = min(self._bottom_most, self._cur_y + n)

    def _cap_cuf(self, n):
        """Moves the cursor right by ``n`` number of positions. """
        for _ in range(n):
            self._cursor_right()

    def _cap_cup(self, y, x):
        """Sets the vertical and horizontal positions of the cursor to ``y``
        and ``x``, respectively. See _cap_vpa and _cap_hpa.

        The ``y`` and ``x`` values start from 1.
        """
        self._cap_vpa(y)
        self._cap_hpa(x)

    def _cap_cvvis(self):
        """Makes the cursor visible. See _cap_civis. """
        self._cur_visible = True

    def _cap_dch(self, n):
        """Deletes ``n`` number of characters. """
        cur_x, cur_y = self._cur_x, self._cur_y
        end = self._peek((cur_x, cur_y), (self._cols, cur_y))
        self._cap_el()
        self._poke((cur_x, cur_y), end[n:])

    def _cap_dch1(self):
        """Deletes a character. """
        self._cap_dch(1)

    def _cap_dim(self):
        """Enters Half-bright mode. """
        pass

    def _cap_dl(self, n):
        """Deletes ``n`` number of lines.

        On the one hand, the specification says that the dl capability should
        delete ``n`` number of lines, on the other hand, in the reality, dl
        just scrolls up ``n`` number of lines. Notice, that dl should work
        together with another capability that will put the cursor on the
        line that is going to be deleted. For example, in tests dl works
        together with the home capability, but it doesn't mean that the
        capabilities are always used together.
        """
        if self._top_most <= self._cur_y <= self._bottom_most:
            for _ in range(n):
                self._scroll_up(self._cur_y + 1, self._bottom_most)

    def _cap_dl1(self):
        """Deletes a line. """
        self._cap_dl(1)

    def _cap_ech(self, n):
        """Erases ``n`` number of characters. """
        self._zero((self._cur_x, self._cur_y), (self._cur_x + n, self._cur_y),
                   inclusively=True)

    def _cap_ed(self):
        """Clears the screen from the current cursor position to the end of the
        screen.
        """
        self._zero((self._cur_x, self._cur_y), (self._cols, self._rows - 1))

    def _cap_el(self):
        """Clears a line from the current cursor position to the end of the
        line without moving the cursor. See _cap_el1.
        """
        self._zero((self._cur_x, self._cur_y), (self._cols, self._cur_y))

    def _cap_el1(self):
        """Clears a line from the beginning to the current cursor position,
        inclusive. The cursor is not moved. See _cap_el.
        """
        self._zero((0, self._cur_y), (self._cur_x, self._cur_y),
                   inclusively=True)

    def _cap_home(self):
        """Moves the cursor to the home position. """
        self._cur_x = 0
        self._cur_y = 0
        self._eol = False

    def _cap_ht(self):
        """Tabs to the next 8-space hardware tab stop. """
        x = self._cur_x + 8
        q, _ = divmod(x, 8)
        self._cur_x = (q * 8) % self._cols

    def _cap_ich(self, n):
        """Inserts ``n`` number of blank characters. """
        for i in range(n):
            self._scroll_right(self._cur_x + i, self._cur_y)

    def _cap_il(self, n):
        """Adds ``n`` number of new blank lines. """
        for _ in range(n):
            if self._cur_y < self._bottom_most:
                self._scroll_down(self._cur_y, self._bottom_most)

    def _cap_il1(self):
        """Adds a new blank line. """
        self._cap_il(1)

    def _cap_ind(self):
        """Scrolls the screen up moving its content down. """
        self._cursor_down()

    def _cap_kb2(self):
        """Handles a Center key-press on keypad. """
        # xterm and Linux console have the kb2 capability, but screen doesn't.
        # Some terminal emulators even handle it in spite of the seeming
        # uselessness of the capability.
        # It's been decided to have a do-nothing handler for kb2.
        pass

    def _cap_kcub1(self):
        """Handles a Left Arrow key-press. """
        self._cur_x = max(0, self._cur_x - 1)
        self._eol = False

    def _cap_kcud1(self):
        """Handles a Down Arrow key-press. """
        self._cap_cud(1)

    def _cap_kcuf1(self):
        """Handles a Right Arrow key-press. """
        self._cap_cuf(1)

    def _cap_kcuu1(self):
        """Handles an Up Arrow key-press. """
        self._cur_y = max(self._top_most, self._cur_y - 1)

    def _cap_op(self):
        """Sets default color-pair to the original one. The name of the
        capability stands for 'original pair'.
        """
        self._set_color_pair(39, 49)

    def _cap_rc(self):
        """Restores the cursor to the last saved position. See _cap_sc. """
        self._cur_x = self._cur_x_bak
        self._cur_y = self._cur_y_bak
        self._eol = True if self._cur_x == self._right_most else False

    def _cap_rev(self):
        """Enables Reverse Video mode. """
        self._set_bit(REVERSE_BIT)

    def _cap_ri(self):
        """Scrolls text down. See _cap_ind. """
        self._cur_y = max(self._top_most, self._cur_y - 1)
        if self._cur_y == self._top_most:
            self._scroll_down(self._top_most, self._bottom_most)

    def _cap_rmir(self):
        """Exits Insert mode. See _cap_smir. """
        pass

    def _cap_rmpch(self):
        """Exits PC character display mode. See _cap_smpch. """
        pass

    def _cap_rmso(self):
        """Exits Standout mode. See _cap_smso. """
        pass

    def _cap_rmul(self):
        """Exits Underline mode. See _cap_smul. """
        self._clean_bit(UNDERLINE_BIT)

    def _cap_rs1(self):
        """Resets terminal completely to sane modes. """
        cells_number = self._cols * self._rows
        self._screen = array.array('Q', [BLACK_AND_WHITE] * cells_number)
        self._sgr = BLACK_AND_WHITE
        self._cur_x_bak = self._cur_x = 0
        self._cur_y_bak = self._cur_y = 0
        self._eol = False
        self._left_most = self._top_most = 0
        self._bottom_most = self._rows - 1
        self._right_most = self._cols - 1

        self._buf = ''
        self._outbuf = ''

    def _cap_sc(self):
        """Saves the current cursor position. See _cap_rc. """
        self._cur_x_bak = self._cur_x
        self._cur_y_bak = self._cur_y

    def _cap_sgr(self, p1=0, p2=0, p3=0, p4=0, p5=0, p6=0, p7=0, p8=0, p9=0):
        """Allows setting arbitrary combinations of modes taking nine
        arguments. The nine arguments are, in order:
        * standout
        * underline
        * reverse
        * blink
        * dim
        * bold
        * blank
        * protect
        * alternate character set
        """
        pass

    def _cap_sgr0(self):
        """Resets all attributes to the default values. """
        self._set_color_pair(0, 10)

    def _cap_smir(self):
        """Enters Insert mode. See _cap_rmir. """
        pass

    def _cap_smso(self):
        """Enters Standout mode. See _cap_rmso.

        John Strang, in his book Programming with Curses, gives the following
        definition for the term. Standout mode is whatever special highlighting
        the terminal can do, as defined in the terminal's database entry.
        """
        pass

    def _cap_smul(self):
        """Enters Underline mode. See _cap_rmul. """
        self._set_bit(UNDERLINE_BIT)

    def _cap_smpch(self):
        """Enters PC character display mode. See _cap_rmpch. """
        pass

    def _cap_vpa(self, y):
        """Sets the vertical position of the cursor to ``y``. See _cap_hpa.

        The ``y`` value starts from 1.
        """
        self._cur_y = min(self._bottom_most, y - 1)

    def _cap_hpa(self, x):
        """Sets the horizontal position of the cursor to ``x``. See _cap_vpa.

        The ``x`` value starts from 1.
        """
        self._cur_x = min(self._right_most, x - 1)
        self._eol = False  # it's necessary to reset _eol after preceding echo

    def _exec_escape_sequence(self):
        """Matches either static escape sequences (such as \E[1m and \E[0;10m)
        or escape sequences with parameters (such as \E[%d@ and \E[%d;%dr) to
        one of the capabilities from the files, containing the matching rules
        (escape sequence to capability). Then the capabilities are executed.
        """
        e = self._buf

        method_name = self._escape_sequences.get(self._buf, None)

        if len(e) > 32:
            self._buf = ''
        elif method_name:  # static sequences
            self._exec_method(method_name)
            self._buf = ''
        else:  # sequences with params
            for k, v in self._escape_sequences_re:
                mo = k.match(e)
                if mo:
                    args = []
                    for i in mo.groups():
                        args.append(int(i))

                    self._exec_method(v, args)
                    e = ''
                    self._buf = ''

    def _exec_single_character_command(self):
        """Executes control sequences like 10 (LF, line feed) or 13 (CR,
        carriage return).
        """
        method_name = self.control_characters[self._buf]
        self._exec_method(method_name)
        self._buf = ''

    def _build_html(self):
        """Transforms the internal representation of the screen into the HTML
        representation.
        """
        self._clean_bit(REVERSE_BIT)

        rows = self._rows
        cols = self._cols
        r = ''

        span = ''  # ready-to-output characters
        span_classes = []
        for i in range(rows * cols):
            cell = self._screen[i]
            q, c = divmod(cell, MAGIC_NUMBER)
            bg, fg = divmod(q, 16)

            current_classes = [
                'b{}'.format(bg),
                'f{}'.format(fg)
            ]

            if self._is_bit_set(UNDERLINE_BIT, cell):
                current_classes.append('underline')

            if self._is_bit_set(REVERSE_BIT, cell):
                current_classes[0] = 'b{}'.format(fg)
                current_classes[1] = 'f{}'.format(bg)

            if self._is_bit_set(BLINK_BIT, cell):
                current_classes.append('blink')

            if self._is_bit_set(BOLD_BIT, cell):
                current_classes.append('bold')

            if i == self._cur_y * cols + self._cur_x and self._cur_visible:
                current_classes[0], current_classes[1] = 'b1', 'f7'  # cursor

            # If the characteristics of the current cell match the
            # characteristics of the previous cell, combine them into a group.
            if span_classes != current_classes or i + 1 == rows * cols:
                if len(span):
                    classes = ' '.join(span_classes)
                    # Replace spaces with non-breaking spaces.
                    ch = html.escape(span.replace(' ', '\xa0'))
                    r += '<span class="{}">{}</span>'.format(classes, ch)
                span = ''
                span_classes = current_classes[:]

            if c == 0:
                span += ' '

            span += chr(c & 0xFFFF)

            if not (i + 1) % cols:
                span += '\n'

        return r

    #
    # User visible methods.
    #
    def generate_html(self, buf):
        """Splits the ``buf`` byte buffer taken from a terminal-oriented
        program into output, escape and control sequences. The output prints on
        the screen as is. The escape and control sequences are executed,
        affecting the output. Finally, the routine generates the HTML document
        which is ready to be printed in a user's browser.
        """
        for i in buf.decode('utf8', errors='replace'):
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

        return self._build_html()
