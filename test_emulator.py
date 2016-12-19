#!/usr/bin/python3
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
import unittest

from terminal import Terminal, MAGIC_NUMBER


class TestEmulator(unittest.TestCase):
    def setUp(self):
        self._rows = 24
        self._cols = 80
        self._terminal = Terminal(self._rows, self._cols)

    def _put_string(self, s, pos):
        """A helper function that puts the string ``s`` to the screen beginning
        with the position ``pos``.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        """

        self._terminal._cur_x, self._terminal._cur_y = pos
        for character in s:
            self._terminal.echo(character)

    def _check_string(self, s, left_border, right_border):
        """A helper function that checks if the screen has the string ``s``
        with a left border starting at position x1, y1, and a right border
        starting at position x2, y2.

        The ``left_border`` and ``right_border`` arguments must be tuples or
        lists of coordinates ``(x1, y1)`` and ``(x2, y2)``, respectively.
        """

        x1, y1 = left_border
        x2, y2 = right_border

        want = array.array('L', [])
        for c in s:
            want.append(self._terminal._sgr | ord(c))

        self.assertEqual(want, self._terminal.peek((x1, y1), (x2, y2)))

    def _check_screen_char(self, c, pos):
        """A helper function that checks if the screen has the character ``c``
        on the corresponding position ``pos``.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        """

        term = self._terminal
        want = term._sgr | ord(c)
        got = term._screen[pos]
        self.assertEqual(want, got)

    def _check_cursor_right(self, cur_x, eol=False):
        """A helper function that checks the `cursor_right` method."""

        self._terminal._cur_x = cur_x
        self._terminal.cursor_right()

        if eol:
            self.assertTrue(self._terminal._eol)
            self.assertEqual(cur_x, self._terminal._cur_x)
        else:
            self.assertFalse(self._terminal._eol)
            self.assertEqual(cur_x + 1, self._terminal._cur_x)

    def _check_cursor_down(self, cur_y, top=False):
        """A helper function that checks the `cursor_down` method."""

        self._terminal._cur_y = cur_y
        self._terminal.cursor_down()

        if top:
            self.assertEqual(cur_y, self._terminal._cur_y)
        else:
            self.assertEqual(cur_y + 1, self._terminal._cur_y)

    def _check_echo(self, c, pos, eol=False):
        """A helper function that checks the `echo` method.

        The ``c`` argument is a character that will be put on the screen
        starting with the position ``pos``.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        Set ``eol`` to True if after calling the `echo` method the cursor will
        be at the end of a line.
        """

        term = self._terminal
        term._eol = False

        cur_x, cur_y = term._cur_x, term._cur_y = pos

        term.echo(c)

        if eol:
            # EOL (end of line) was reached, cur_x position must no be changed.
            self.assertTrue(term._eol)
            self.assertEqual(cur_x, term._cur_x)
            check_screen_pos = term._cur_y * term._cols + term._cur_x
        else:
            # EOL (end of line) was not reached, cur_x was moved right by 1
            # position.
            self.assertFalse(term._eol)
            self.assertEqual(cur_x + 1, term._cur_x)
            check_screen_pos = term._cur_y * term._cols + (term._cur_x - 1)

        # Check if the screen has the correct character on the corresponding
        # position.
        self._check_screen_char(c, check_screen_pos)

    def _check_zero(self, s, pos):
        """A helper function that checks the `zero` method.

        The ``s`` argument is a string that will be removed from the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        """

        term = self._terminal
        cur_x, cur_y = pos

        self._put_string(s, pos)
        self._check_string(s, pos, (cur_x + len(s), cur_y))

        clear_len = term.zero(pos, (cur_x + len(s), cur_y))

        self.assertEqual(len(s), clear_len)

        clear_area = array.array('L', [MAGIC_NUMBER] * len(s))
        self.assertEqual(clear_area, term.peek(pos, (cur_x + len(s), cur_y)))

    def _check_scroll_up(self, s, pos):
        """A helper function that checks the `scroll_up` method.

        The ``s`` argument is a test string that will be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        """

        x, y = pos
        term = self._terminal

        self._put_string(s, pos)
        self._check_string(s, pos, (x + len(s), y))

        # Scroll up the whole screen.
        term.scroll_up(0, term._bottom)

        self._check_string(s, (x, y - 1), (x + len(s), y - 1))

        want = array.array('L', [MAGIC_NUMBER] * term._right)
        got = term.peek(pos, (term._right, y))
        self.assertEqual(want, got)

        # Restore the initial position of the screen.
        term.zero((0, 0), (term._right, term._bottom))

    def _check_scroll_down(self, s, pos):
        """A helper function that checks the `scroll_down` method.

        The ``s`` argument is a test string that will be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        """

        x, y = pos
        term = self._terminal

        self._put_string(s, pos)
        self._check_string(s, pos, (x + len(s), y))

        # Scroll down the whole screen.
        term.scroll_down(0, term._bottom)

        self._check_string(s, (x, y + 1), (x + len(s), y + 1))

        want = array.array('L', [MAGIC_NUMBER] * term._right)
        got = term.peek(pos, (term._right, y))
        self.assertEqual(want, got)

        # Restore the initial position of the screen.
        term.zero((0, 0), (term._right, term._bottom))

    def _check_scroll_right(self, s, pos):
        """A helper function that checks the screen scrolling right.

        The ``s`` argument is a test string putting on the screen.
        The ``pos`` argument is a tuple or list of coordinates ``(x, y)``.
        """
        x, y = pos
        term = self._terminal

        self._put_string(s, pos)
        self._check_string(s, pos, (x + len(s), y))

        term.scroll_right(x, y)

        self._check_string(s, (x + 1, y), (x + len(s) + 1, y))

        # Restore the initial position of the screen.
        term.zero((0, 0), (term._right, term._bottom))

    def test_cursor_right(self):
        """The terminal should move the cursor right by 1 position."""

        # Cursor is on the left-most position.
        self._check_cursor_right(0)

        # Cursor is on an arbitrary position.
        rand_x = random.randint(1, self._cols - 2)
        self._check_cursor_right(rand_x)

        # Cursor is on the right-most position.
        self._check_cursor_right(self._terminal._right, eol=True)

    def test_cursor_down(self):
        """The terminal should move the cursor down by 1 position."""

        # Cursor is on the top-most position.
        self._check_cursor_down(0)

        # Cursor is on an arbitrary position.
        rand_y = random.randint(1, self._terminal._bottom - 1)
        self._check_cursor_down(rand_y)

        # Cursor is on the down-most position.
        self._check_cursor_down(self._terminal._right, top=True)

    def test_echo(self):
        """The terminal should put the specified character on the screen and
        move the cursor right by 1 position.
        """

        term = self._terminal

        # Echo the character on the screen (left-most position).
        self._check_echo('d', (0, 0))

        # Echo the character on an arbitrary position on the screen.
        rand_cur_x = random.randint(1, self._cols - 2)
        rand_cur_y = random.randint(1, term._bottom - 1)
        self._check_echo('r', (rand_cur_x, rand_cur_y))

        # Echo the character on the screen (right-most position).
        self._check_echo('a', (term._right, rand_cur_y), eol=True)

        # Echo the character on the screen (right-most position).
        self._check_echo('p', (term._right, term._bottom), eol=True)

    def test_echo_eol(self):
        """The terminal should move the cursor to the next line when the
        current position of the cursor is at the end of a line.
        """

        term = self._terminal

        # Put the cursor to the right-most position - 1
        term._cur_x = term._cols - 2

        # Put a character to move the cursor to the right-most position
        term.echo('e')

        # After putting another character we will reach the end of the line
        term.echo('g')
        self.assertTrue(term._eol)

        # After putting one more character the cursor will be moved to the next
        # line
        term.echo('g')
        self.assertEqual(1, term._cur_x)
        self.assertEqual(1, term._cur_y)
        self.assertFalse(term._eol)

    def test_zero(self):
        """The terminal should clear the area from a left border starting at
        position x1, y1 to a right border starting at position x2, y2.
        """

        term = self._terminal

        # Clear the first line.
        self._check_zero(['s'] * term._right, (0, 0))

        # Clear the last line.
        self._check_zero(['p'] * term._right, (0, term._bottom))

        # Clear a random number of lines.
        rand_x = random.randint(1, self._cols - 2)
        rand_y = random.randint(1, term._bottom - 1)
        rand_len = random.randint(1, term._right - rand_x)
        self._check_zero(['a'] * rand_len, (rand_x, rand_y))

        # Clear the whole screen.
        self._check_zero(['m'] * term._right * term._bottom, (0, 0))

    def test_scroll_up(self):
        """The terminal should move an area by 1 line up."""

        term = self._terminal

        # Scroll up the first line.
        self._check_scroll_up(['f'] * term._right, (0, 1))

        # Scroll up the last line.
        self._check_scroll_up(['l'] * term._right, (0, term._bottom))

        # Scroll up the random line.
        rand_y = random.randint(2, term._bottom - 1)
        self._check_scroll_up(['r'] * term._right, (0, rand_y))

    def test_scroll_down(self):
        """The terminal should move an area by 1 line down."""

        term = self._terminal

        # Scroll down the first line.
        self._check_scroll_down(['f'] * term._right, (0, 0))

        # Scroll down the last line.
        self._check_scroll_down(['l'] * term._right, (0, term._bottom - 1))

        # Scroll down the random line.
        rand_y = random.randint(2, term._bottom - 2)
        self._check_scroll_down(['r'] * term._right, (0, rand_y))

    def test_scroll_right(self):
        """The terminal should move area by 1 position right."""

        term = self._terminal

        # Scroll right the string (begin at left-most position).
        self._check_scroll_right('test', (0, 0))

        # Scroll right the string (begin at random position).
        s = 'test'
        self._check_scroll_right(s,
                                 (random.randint(1, term._right - len(s)),
                                  random.randint(1, term._bottom)))

    def test_peek(self):
        """The terminal should have the possibility of capturing the area from
        a left border starting at position x1, y1 to a right border starting at
        position x2, y2.
        """

        term = self._terminal

        start = 3
        end = 7
        zeros = array.array('L', [0] * (end - start))

        # The last '0' will be on the 6th position
        term._screen[start:end] = zeros

        # Get an area from the 3rd to the 6th character
        got = term.peek((start, 0), (end, 0))
        self.assertEqual(zeros, got)

        # Get an area from the 3rd to the 7th character
        got = term.peek((start, 0), (end, 0), inclusively=True)
        zeros.append(MAGIC_NUMBER)
        self.assertEqual(zeros, got)

    def test_poke(self):
        """The terminal should have the possibility of putting the specified
        string on the screen staring at the specified position.
        """

        term = self._terminal

        start = 3
        end = 7
        zeros = array.array('L', [0] * (end - start))

        # The last '0' will be on the 6th position
        term.poke((start, 0), zeros)

        # Get an area from the 3rd to the 6th character
        got = term.peek((start, 0), (end, 0))
        self.assertEqual(zeros, got)

    def test_cap_ed(self):
        """The terminal should have the possibility of clearing the screen from
        the current cursor position to the end of the screen.
        """

        term = self._terminal

        prompt = 'spam@ham:~$ '
        self._put_string(prompt, (0, 0))  # put a prompt on the screen

        # Check that the prompt was put correctly
        self._check_string(prompt, (0, 0), (len(prompt), 0))

        # Fill the rest of the screen with x
        length = term._cols * term._rows - len(prompt)
        self._put_string(['x'] * length, (len(prompt), 0))

        # Clear the screen after the prompt till the end of the screen
        term._cur_x = len(prompt)
        term._cur_y = 0
        term.cap_ed()

        # Check that the prompt was not corrupted
        self._check_string(prompt, (0, 0), (len(prompt), 0))

        # Check that the screen was cleared correctly
        want = array.array('L', [MAGIC_NUMBER] * length)
        got = term.peek((term._cur_x, 0), (term._right, term._bottom),
                        inclusively=True)
        self.assertEqual(want, got)

    def test_cap_rs1(self):
        """The terminal should have the possibility to completely reset to sane
        mode.
        """

        # Exec some operations with terminal.
        self._terminal.echo('a')
        self._terminal.cursor_right()
        self._terminal.cursor_down()
        self._terminal.scroll_down(0, self._terminal._bottom)

        # Reset the terminal to the sane mode.
        self._terminal.cap_rs1()
        self.assertEqual(0, self._terminal._cur_x)
        self.assertEqual(0, self._terminal._cur_y)
        self.assertFalse(self._terminal._eol)

    def _check_esc_0x08(self, pos, want_cur_x):
        """A helper function that checks the `esc_0x08` method.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        The ``want_cur_x`` argument is an expected terminal's `cur_x` value
        after `esc_0x08` method.
        """

        term = self._terminal
        term._cur_x, term._cur_y = pos
        term.esc_0x08('')
        self.assertEqual(want_cur_x, term._cur_x)

    def test_esc_0x08(self):
        """The terminal should have the possibility to set cursor's `x` position
        to maximum between `0` and current cursor position - 1.
        """

        term = self._terminal

        # Cursor at the left-most position.
        self._check_esc_0x08((0, 0), want_cur_x=0)

        # Cursor at the right-most position.
        self._check_esc_0x08((term._right, 0), want_cur_x=term._right - 1)

        # Set cursor's `x` position to random.
        rand_x = random.randint(1, term._right - 1)
        self._check_esc_0x08((rand_x, 0), want_cur_x=rand_x - 1)

    @unittest.skip("skip")
    def test_esc_0x09(self):
        # ATTN: need a decription.
        pass

    def test_esc_0x0a(self):
        """The terminal should have the possibility to move cursor down by 1
        position.
        """

        # Cursor at left-most position.
        self._terminal.esc_0x0a('')
        self.assertEqual(1, self._terminal._cur_y)

    def _check_esc_0x0d(self, pos):
        """A helper function that checks `esc_0x0d` method.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        """

        term = self._terminal
        term._cur_x, term._cur_y = pos

        self._terminal.esc_0x0d('')
        self.assertEqual(0, self._terminal._cur_x)
        self.assertFalse(self._terminal._eol)

    def test_esc_0x0d(self):
        """The terminal should have the possibility to set cursor at beginning
        of the line.
        """

        # Cursor at left-most position.
        self._check_esc_0x0d((0, 0))

        # Cursor at right-most position.
        self._check_esc_0x0d((self._terminal._right, 0))

        # Cursor at random position.
        self._check_esc_0x0d((random.randint(1, self._terminal._right), 0))

    @unittest.skip("skip")
    def test_esc_da(self):
        # ATTN: need a decription.
        pass

    def test_esc_ri(self):
        """The terminal should scroll down by 1 position when terminal's `top`
        was chosen as maximum between terminal's `top` and terminal's `cur_y`.
        """
        
        # Cursor at left-most position, `top` and `cur_y` equal 0.
        s = ['a'] * self._terminal._right
        self._put_string(s, (0, 0))
        self._terminal.esc_ri('')
        self._check_string(s, (0, 1), (len(s), 1))

        # Reset the terminal to the sane mode.
        self._terminal.cap_rs1()

        # Put `cur_y` at random position.
        rand_y = random.randint(1, self._terminal._bottom)
        self._terminal._cur_y = rand_y
        self._terminal.esc_ri('')
        self.assertEqual(rand_y - 1, self._terminal._cur_y)

    @unittest.skip("skip")
    def test_cap_set_colour_pair(self):
        pass

    @unittest.skip("skip")
    def test_cap_set_colour(self):
        pass

    @unittest.skip("skip")
    def test_cap_sgr0(self):
        pass

    @unittest.skip("skip")
    def test_cap_op(self):
        pass

    @unittest.skip("skip")
    def test_cap_noname(self):
        pass

    @unittest.skip("skip")
    def test_cap_bold(self):
        pass

    @unittest.skip("skip")
    def test_cap_dim(self):
        pass

    @unittest.skip("skip")
    def test_cap_smul(self):
        pass

    @unittest.skip("skip")
    def test_cap_blink(self):
        pass

    @unittest.skip("skip")
    def test_cap_smso_rev(self):
        pass

    @unittest.skip("skip")
    def test_cap_rmpch(self):
        pass

    @unittest.skip("skip")
    def test_cap_smpch(self):
        pass

    @unittest.skip("skip")
    def test_cap_rmul(self):
        pass

    @unittest.skip("skip")
    def test_cap_rmso(self):
        pass

    def test_cap_sc(self):
        """The terminal should have the possibility to save current cursor
        position.
        """

        term = self._terminal
        x, y = random.randint(0, term._right), random.randint(0, term._bottom)
        term._cur_x, term._cur_y = x, y
        term.cap_sc()

        self.assertEqual(x, term._cur_x_bak)
        self.assertEqual(y, term._cur_y_bak)

    def test_cap_rc(self):
        """The terminal should have the possibility to set cursor's position to
        recently saved position.
        """
        term = self._terminal

        # Put the cursor to the right-most position - 1
        term._cur_x = term._right - 1

        # Put a character to move the cursor to the right-most position
        term.echo('e')

        # After putting another character we will reach the end of the line
        term.echo('g')
        self.assertTrue(term._eol)

        cur_x_bck = term._cur_x
        term.cap_sc()  # save the cursor's current position

        # Put one more character to move the cursor to the next line
        term.echo('g')

        term.cap_rc()  # restore a previously saved cursor's position
        self.assertEqual(cur_x_bck, term._cur_x)
        self.assertTrue(term._eol)

    @unittest.skip('skip')
    def test_cap_ich1(self):
        # ATTN: corresponding method has the following doc: Insert character.
        #       Is it ok? I'm confused because this method just executes
        #       `scroll_right` terminal method.

        """The terminal should have the possibility to insert character. """
        pass

    def test_cap_smso(self):
        """The terminal should have the possibility to begin standout mode. """

        self._terminal._sgr = None
        self._terminal.cap_smso()
        self.assertEqual(0x70000000, self._terminal._sgr)

    def _check_cap_kcuu1(self, pos, want_cur_y):
        """A helper function that checks `cap_kcuu1` method.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        The ``want_cur_y`` argument is an expected terminal's `cur_y` value
        after `cap_kcud1` method.
        """

        self._terminal._cur_x, self._terminal._cur_y = pos
        self._terminal.cap_kcuu1()
        self.assertEqual(want_cur_y, self._terminal._cur_y)

        self._terminal.cap_rs1()

    def test_cap_kcuu1(self):
        """The terminal should have the possibility to receive string of input
        characters sent by typing the up-arrow key.
        """

        term = self._terminal

        # Terminal's `cur_y` is on the top-most position.
        self._check_cap_kcuu1((0, 0), term._top)

        # Terminal's `cur_y` is on the bottom-most position.
        self._check_cap_kcuu1((0, term._bottom), term._bottom - 1)

        # Terminal's `cur_y` is on the random position.
        rand_y = random.randint(1, term._bottom - 1)
        self._check_cap_kcuu1((0, rand_y), rand_y - 1)

    def _check_cap_kcud1(self, pos, want_cur_y):
        """A helper function that checks `cap_kcud1` method.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        The ``want_cur_y`` argument is an expected terminal's `cur_y` value
        after `cap_kcud1` method.
        """

        self._terminal._cur_x, self._terminal._cur_y = pos
        self._terminal.cap_kcud1()
        self.assertEqual(want_cur_y, self._terminal._cur_y)

        self._terminal.cap_rs1()

    def test_cap_kcud1(self):
        """The terminal should have the possibility to receive string of input
        characters sent by typing the down-arrow key.
        """

        term = self._terminal

        # Terminal's `cur_y` is on the top-most position.
        self._check_cap_kcud1((0, 0), 1)

        # Terminal's `cur_y` is on the bottom-most position.
        self._check_cap_kcud1((0, term._bottom), term._bottom)

        # Terminal's `cur_y` is on the random position.
        rand_y = random.randint(1, term._bottom - 1)
        self._check_cap_kcud1((0, rand_y), rand_y + 1)

    @unittest.skip('skip')
    def test_cap_kcuf1(self):
        pass

    @unittest.skip("skip")
    def test_cap_cuf(self):
        pass

    @unittest.skip("skip")
    def test_cap_kcub1(self):
        pass

    @unittest.skip("skip")
    def test_cap_kb2(self):
        pass

    @unittest.skip("skip")
    def test_cap_home(self):
        """The terminal should have the possibility to set cursor to the home
        position (the upper left corner).
        """
        pass

    @unittest.skip("skip")
    def test_cap_el(self):
        """The emulator should have the possibility to clear the screen from the
        current cursor position to the end of line.
        """
        pass

    @unittest.skip("skip")
    def test_cap_el1(self):
        pass

    @unittest.skip("skip")
    def test_cap_il1(self):
        """The terminal should have the possibility to add new blank line. """
        pass

    @unittest.skip('skip')
    def test_cap_dl1(self):
        """The terminal should have the possibility to delete a line. """
        pass

    @unittest.skip('skip')
    def test_cap_dch1(self):
        """The terminal should have the possibility to delete a character. """
        pass

    @unittest.skip('skip')
    def test_cap_vpa(self):
        pass

    @unittest.skip('skip')
    def test_cap_il(self):
        pass

    @unittest.skip('skip')
    def test_cap_dl(self):
        pass

    @unittest.skip('skip')
    def test_cap_dch(self):
        pass

    @unittest.skip('skip')
    def test_cap_csr(self):
        pass

    @unittest.skip('skip')
    def test_cap_ech(self):
        pass

    @unittest.skip('skip')
    def test_cap_cup(self):
        pass

    @unittest.skip('skip')
    def test_exec_escape_sequence(self):
        pass


if __name__ == '__main__':
    unittest.main()
