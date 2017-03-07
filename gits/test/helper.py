# Copyright 2016 Dmitriy Shilin <sdadeveloper@gmail.com>
# Copyright 2016 Evgeny Golyshev <eugulixes@gmail.com>
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
import random
import string
import unittest

from gits.terminal import Terminal, BLACK_AND_WHITE


def reset_after_executing(func):
    """Resets the terminal to sane modes after executing a decorated helper.
    """
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        self._terminal._cap_rs1()

    return wrapper


class Helper(unittest.TestCase):
    def setUp(self):
        self._rows = 24
        self._cols = 80
        self._terminal = Terminal(self._rows, self._cols)

    def _put_string(self, s, pos):
        """A helper that puts the specified string on the screen.

        The ``s`` argument is the string to be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want to place the string.
        """
        self._terminal._cur_x, self._terminal._cur_y = pos
        for character in s:
            self._terminal._echo(character)

    def _get_random_string(self, n):
        """Generates a random string.

        The ``n`` argument is the length of the target string.
        """
        chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
        return ''.join(random.SystemRandom().choice(chars) for _ in range(n))

    def _check_string(self, s, left_border, right_border):
        """A helper that checks if the screen has the string ``s`` between
        ``left_border`` and ``right_border``.

        The ``left_border`` and ``right_border`` arguments must be tuples or
        lists of coordinates ``(x1, y1)`` and ``(x2, y2)``, respectively.
        """
        x1, y1 = left_border
        x2, y2 = right_border

        term = self._terminal

        want = array.array('Q', [])
        for c in s:
            want.append(term._sgr | ord(c))

        self.assertEqual(want, term._peek((x1, y1), (x2, y2)))

    def _check_screen_char(self, c, pos):
        """A helper that checks if the screen has the specified character.

        The ``c`` argument is the target character.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the character to be.
        """
        term = self._terminal
        want = term._sgr | ord(c)
        got = term._screen[pos]
        self.assertEqual(want, got)

    def _check_cursor_right(self, cur_x, eol=False):
        """A helper that checks the `_cursor_right` method.

        The ``cur_x`` argument is the x position of the cursor.
        The ``eol`` argument enables checking reaching the end of a line.
        """
        self._terminal._cur_x = cur_x
        self._terminal._cursor_right()

        if eol:
            self.assertTrue(self._terminal._eol)
            self.assertEqual(cur_x, self._terminal._cur_x)
        else:
            self.assertFalse(self._terminal._eol)
            self.assertEqual(cur_x + 1, self._terminal._cur_x)

    def _check_cursor_down(self, cur_y, top=False):
        """A helper that checks the `_cursor_down` method.

        The ``cur_y`` argument is the y position of the cursor.
        The ``top`` argument enables checking that the y position doesn't
        change when the cursor is at the top-most position.
        """
        self._terminal._cur_y = cur_y
        self._terminal._cursor_down()

        if top:
            self.assertEqual(cur_y, self._terminal._cur_y)
        else:
            self.assertEqual(cur_y + 1, self._terminal._cur_y)

    def _check_echo(self, c, pos, eol=False):
        """A helper that checks the `_echo` method.

        The ``c`` argument is a character to be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the character to be.
        The ``eol`` argument enables checking reaching the end of a line.
        """
        term = self._terminal
        term._eol = False

        cur_x, _ = term._cur_x, term._cur_y = pos

        term._echo(c)

        if eol:
            # If the end of a line was reached, the x position of the cursor
            # must not be changed.
            self.assertTrue(term._eol)
            self.assertEqual(cur_x, term._cur_x)
            check_screen_pos = term._cur_y * term._cols + term._cur_x
        else:
            # If the end of a line was not reached, the x position of the
            # cursor must be moved right by 1 position.
            self.assertFalse(term._eol)
            self.assertEqual(cur_x + 1, term._cur_x)
            check_screen_pos = term._cur_y * term._cols + (term._cur_x - 1)

        # Check if the screen has the correct character on the corresponding
        # position.
        self._check_screen_char(c, check_screen_pos)

    def _check_zero(self, s, pos):
        """A helper that checks the `_zero` method.

        The ``s`` argument is a test string to be removed from the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the string to be.
        """
        term = self._terminal
        cur_x, cur_y = pos

        self._put_string(s, pos)
        self._check_string(s, pos, (cur_x + len(s), cur_y))

        clear_len = term._zero(pos, (cur_x + len(s), cur_y))

        self.assertEqual(len(s), clear_len)

        clear_area = array.array('Q', [BLACK_AND_WHITE] * len(s))
        self.assertEqual(clear_area, term._peek(pos, (cur_x + len(s), cur_y)))

    def _check_scroll_down(self, s, pos):
        """A helper that checks the `_scroll_down` method.

        The ``s`` argument is a test string to be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the string to be.
        """
        x, y = pos
        term = self._terminal

        self._put_string(s, pos)
        self._check_string(s, pos, (x + len(s), y))

        # Scroll down the whole screen.
        term._scroll_down(0, term._bottom_most)

        self._check_string(s, (x, y + 1), (x + len(s), y + 1))

        want = array.array('Q', [BLACK_AND_WHITE] * term._right_most)
        got = term._peek(pos, (term._right_most, y))
        self.assertEqual(want, got)

        # Restore the initial position of the screen.
        term._zero((0, 0), (term._right_most, term._bottom_most))

    def _check_scroll_right(self, s, pos):
        """A helper that checks the `_scroll_right` method.

        The ``s`` argument is a test string to be put on the screen.
        The ``pos`` argument is a tuple or list of coordinates ``(x, y)``
        of the location where you want the string to be.
        """
        x, y = pos
        term = self._terminal

        self._put_string(s, pos)
        self._check_string(s, pos, (x + len(s), y))

        term._scroll_right(x, y)

        self._check_string(s, (x + 1, y), (x + len(s) + 1, y))

        # Restore the initial position of the screen.
        term._zero((0, 0), (term._right_most, term._bottom_most))

    @reset_after_executing
    def _check_scroll_up(self, s, pos):
        """A helper that checks the `_scroll_up` method.

        The ``s`` argument is a test string to be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the string to be.
        """
        x, y = pos
        term = self._terminal

        self._put_string(s, pos)
        self._check_string(s, pos, (x + len(s), y))

        term._scroll_up(y, y + 1)

        # Check that the line was moved correctly.
        self._check_string(s, (x, y - 1), (x + len(s), y - 1))

        # Check that the place, where the line used to be, is filled with
        # zeros.
        want = array.array('Q', [BLACK_AND_WHITE] * term._cols)
        got = term._peek(pos, (term._right_most, y), inclusively=True)
        self.assertEqual(want, got)

    @reset_after_executing
    def _check_peek(self, s, pos):
        """A helper that checks the `_peek` method.

        The ``s`` argument is a test string to be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the string to be.
        """
        x, y = pos

        self._put_string(s, pos)
        self._check_string(s, pos, (x + len(s), y))

    def _check_poke(self, s, pos):
        """A helper that checks the `_poke` method.

        The ``s`` argument is a test slice to be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the slice to be.
        """
        term = self._terminal
        x, y = pos

        term._poke(pos, s)
        got = term._peek((x, y), (x + len(s), y))
        self.assertEqual(s, got)

    def _check_cap_cr(self, pos):
        """A helper that checks the `_cap_cr` method.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the initial position of the cursor.
        """
        term = self._terminal
        term._cur_x, term._cur_y = pos

        self._terminal._cap_cr()
        self.assertEqual(0, self._terminal._cur_x)
        self.assertFalse(self._terminal._eol)

    def _check_cap_cub1(self, pos):
        """A helper that checks the `_cap_cub1` method.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the initial position of the cursor.
        """
        term = self._terminal
        cur_x, cur_y = pos
        term._cur_x, term._cur_y = pos

        term._cap_cub1()

        if cur_x == 0:
            self.assertEqual(term._left_most, term._cur_x)
        else:
            self.assertEqual(cur_x - 1, term._cur_x)
            self.assertEqual(cur_y, term._cur_y)

    @reset_after_executing
    def _check_cap_cup(self, pos):
        """A helper that checks the `_cap_cup` method.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        you want the cursor to be set to via `_cap_cup`.
        """
        x, y = pos

        term = self._terminal

        term._cap_cup(y, x)

        # The y and x values start from 1.
        self.assertEqual(x - 1, term._cur_x)
        self.assertEqual(y - 1, term._cur_y)
        self.assertFalse(term._eol)

    @reset_after_executing
    def _check_cap_csr(self, reg):
        """ A helper that checks the `_cap_csr` method.

        The ``reg`` argument must be a tuple or list of lines ``(top, bottom)``
        you want the scrolling region to be set to via `_cap_csr`.
        """
        top, bottom = reg
        term = self._terminal

        term._cap_csr(top, bottom)

        if top > bottom:
            self.assertEqual(top - 1, term._bottom_most)
        else:
            self.assertEqual(bottom - 1, term._bottom_most)
        self.assertEqual(top - 1, term._top_most)

    @reset_after_executing
    def _check_cap_dl(self, n, lines):
        """A helper that checks the `_cap_dl` method.

        The ``n`` argument is a number of lines to be deleted from the screen.
        The ``lines`` argument must be a list of tuples ``(line, pos)``, where
        ``line`` is a test string to be put on the screen, ``pos`` is a tuple
        or list of coordinates ``(x, y)`` of the location where you want the
        string to be.
        """
        term = self._terminal

        for line, pos in lines:
            self._put_string(line, pos)
            term._eol = False

        # We have to put the cursor on the line that is going to be deleted.
        # In this particular case, the home capability does what we really
        # want, but it doesn't mean that the capabilities are always used
        # together. Moreover, it's quite difficult to find a program which
        # uses dl. As far as we know, vi, nano, top, htop and mc don't use it.
        term._cap_home()

        term._cap_dl(n)

        if len(lines) == n:
            line = lines[0]
            x, y = line[1]
            s = line[0]

            want = array.array('Q', [BLACK_AND_WHITE] * len(s))
            got = term._peek((x, y), (len(s), y))
            self.assertEqual(want, got)
        else:
            lines = lines[n:len(lines)-1]
            for i, line in enumerate(lines):
                x, _ = line[1]
                s = line[0]
                self._check_string(s, (x, i), (len(s), i))

    @reset_after_executing
    def _check_cap_dch(self, s, n):
        """A helper that checks the `_cap_dch` method.

        The ``s`` argument is a test string to be put on the screen.
        The ``n`` argument is a number of characters to be deleted from the
        string.
        """
        term = self._terminal

        self._put_string(s, (0, 0))
        self._check_string(s, (0, 0), (len(s), 0))

        term._cur_x, term._cur_y = 0, 0

        term._cap_dch(n)
        self._check_string(s[n:], (0, 0), (len(s[n:]), 0))

    def _check_cap_ech(self, s, pos, n):
        """A helper that checks the `_cap_ech` method.

        The ``s`` argument is a test string to be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the string to be.
        The ``n`` argument is a number of characters you want to be erased via
        `_cap_ech`.
        """
        term = self._terminal
        cur_x, cur_y = pos

        self._put_string(s, pos)
        term._cur_x, term._cur_y = pos

        term._cap_ech(n)

        clear_area = array.array('Q', [BLACK_AND_WHITE] * n)
        self.assertEqual(clear_area, term._peek(pos, (cur_x + n, cur_y)))

    @reset_after_executing
    def _check_cap_el(self, s, pos):
        """A helper that checks the `_cap_el` method.

        The ``s`` argument is a test string to be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the string to be.
        """
        cur_x, cur_y = pos

        self._put_string(s, pos)
        self._check_string(s, pos, (cur_x + len(s), cur_y))

        term = self._terminal
        term._cur_x, term._cur_y = pos

        term._cap_el()

        want = array.array('Q', [BLACK_AND_WHITE] * (term._right_most - cur_x))
        got = term._peek(pos, (term._right_most, cur_y))
        self.assertEqual(want, got)

    @reset_after_executing
    def _check_cap_el1(self, s, pos):
        """A helper that checks the `_cap_el1` method.

        The ``s`` argument is a test string to be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the string to be.
        """
        cur_x, cur_y = pos

        self._put_string(s, pos)

        term = self._terminal
        term._cur_x, term._cur_y = pos

        term._cap_el1()

        want = array.array('Q', [BLACK_AND_WHITE] * cur_x)
        got = term._peek((0, cur_y), (cur_x, cur_y))
        self.assertEqual(want, got)

    @reset_after_executing
    def _check_cap_home(self, pos):
        """A helper that checks the `_cap_home` method.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the initial position of the cursor.
        """
        term = self._terminal
        term._cur_x, term._cur_y = pos
        term._cap_home()

        self.assertEqual(0, term._cur_x)
        self.assertEqual(0, term._cur_y)
        self.assertFalse(term._eol)

    def _check_cap_hpa(self, x):
        """A helper that checks the `_cap_hpa` method.

        The ``x`` argument is the horizontal position you want the cursor to be
        set to.
        """
        term = self._terminal

        term._cap_hpa(x)

        self.assertEqual(x - 1, term._cur_x)
        self.assertFalse(term._eol)

    @reset_after_executing
    def _check_cap_il1(self, s, pos):
        """A helper that checks the `_cap_il1` method.

        The ``s`` argument is a test string to be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the string to be.
        """
        cur_x, cur_y = pos

        self._put_string(s, pos)

        term = self._terminal
        term._cur_x, term._cur_y = pos

        term._cap_il1()

        self.assertEqual(cur_x, term._cur_x)

        if cur_y == term._bottom_most:
            self._check_string(s, pos, (cur_x + len(s), cur_y))
        else:
            self._check_string(s, (cur_x, cur_y + 1),
                               (cur_x + len(s), cur_y + 1))

            want = array.array('Q', [BLACK_AND_WHITE] * term._right_most)
            got = term._peek((0, cur_y), (term._right_most, cur_y))
            self.assertEqual(want, got)

    @reset_after_executing
    def _check_cap_kcub1(self, pos):
        """A helper that checks the `_cap_kcub1` method.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the initial position of the cursor.
        """
        term = self._terminal
        x, _ = pos
        term._cur_x, term._cur_y = pos

        term._cap_kcub1()

        self.assertFalse(term._eol)
        if x == 0:
            self.assertEqual(0, term._cur_x)
        else:
            self.assertEqual(x - 1, term._cur_x)

    @reset_after_executing
    def _check_cap_kcud1(self, pos, want_cur_y):
        """A helper that checks the `_cap_kcud1` method.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the initial position of the cursor.
        The ``want_cur_y`` argument is an expected y position of the cursor
        after calling the `cap_kcud1` method.
        """
        self._terminal._cur_x, self._terminal._cur_y = pos
        self._terminal._cap_kcud1()
        self.assertEqual(want_cur_y, self._terminal._cur_y)

    @reset_after_executing
    def _check_cap_kcuu1(self, pos, want_cur_y):
        """A helper that checks the `_cap_kcuu1` method.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the initial position of the cursor.
        The ``want_cur_y`` argument is an expected y position of the cursor
        after calling the `cap_kcud1` method.
        """
        self._terminal._cur_x, self._terminal._cur_y = pos
        self._terminal._cap_kcuu1()
        self.assertEqual(want_cur_y, self._terminal._cur_y)

    @reset_after_executing
    def _check_cap_ri(self, s, pos):
        """A helper that checks the `_cap_ri` method.

        The ``s`` argument is the string to be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``
        of the location where you want the string to be.
        """
        term = self._terminal
        x, y = pos

        self._put_string(s, pos)
        term._cur_x, term._cur_y = pos

        term._cap_ri()

        if y == 0:
            self.assertEqual(y, term._cur_y)
            self._check_string(s, (x, y + 1), (x + len(s), y + 1))
        elif y == 1:
            self.assertEqual(y - 1, term._cur_y)
            self._check_string(s, (x, y + 1), (x + len(s), y + 1))
        else:
            self.assertEqual(y - 1, term._cur_y)
            self._check_string(s, (x, y), (x + len(s), y))

    def _check_cap_vpa(self, y):
        """A helper that checks the `_cap_vpa` method.

        The ``y`` argument is the vertical position you want the cursor to be
        set to.
        """
        self._terminal._cap_vpa(y)
        self.assertEqual(y - 1, self._terminal._cur_y)
