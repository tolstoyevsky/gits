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

from gits.terminal import (
    BLACK_AND_WHITE,
    UNDERLINE_BIT,
    REVERSE_BIT,
    BLINK_BIT,
    BOLD_BIT,
)
from gits.test.helper import Helper


class TestCapabilities(Helper):
    def test_cursor_down(self):
        """The terminal should have the possibility to move the cursor down by
        1 position."""
        self._check_cursor_down(0)
        self._check_cursor_down(self._terminal._bottom_most, top=True)

        rand_y = random.randint(1, self._terminal._bottom_most - 1)
        self._check_cursor_down(rand_y)

    def test_cursor_right(self):
        """The terminal should have the possibility to move the cursor right by
        1 position.
        """
        self._check_cursor_right(0)

        rand_x = random.randint(1, self._cols - 2)
        self._check_cursor_right(rand_x)

        self._check_cursor_right(self._terminal._right_most, eol=True)

    def test_echo(self):
        """The terminal should have the possibility to put the specified
        character on the screen and move the cursor right by 1 position.
        """
        term = self._terminal

        self._check_echo('d', (0, 0))

        rand_cur_x = random.randint(1, term._right_most - 1)
        rand_cur_y = random.randint(1, term._bottom_most - 1)
        self._check_echo('r', (rand_cur_x, rand_cur_y))

        self._check_echo('a', (term._right_most, rand_cur_y), eol=True)

        self._check_echo('p', (term._right_most, term._bottom_most), eol=True)

    def test_echo_eol(self):
        """The terminal should have the possibility to move the cursor to the
        next line when the current position of the cursor is at the end of a
        line.
        """
        term = self._terminal
        term._cur_x = term._right_most - 1

        # Put a character to move the cursor to the right-most position.
        term._echo('e')

        # After putting another character we will reach the end of the line.
        term._echo('g')
        self.assertTrue(term._eol)

        # After putting one more character the cursor will be moved to the
        # next line.
        term._echo('g')
        self.assertEqual(1, term._cur_x)
        self.assertEqual(1, term._cur_y)
        self.assertFalse(term._eol)

    def test_zero(self):
        """The terminal should have the possibility to clear the area from a
        left border starting at position x1, y1 to a right border starting at
        position x2, y2.
        """
        term = self._terminal

        self._check_zero(['s'] * term._right_most, (0, 0))
        self._check_zero(['p'] * term._right_most, (0, term._bottom_most))
        self._check_zero(['m'] * term._right_most * term._bottom_most, (0, 0))

        rand_x = random.randint(1, self._cols - 2)
        rand_y = random.randint(1, term._bottom_most - 1)
        rand_len = random.randint(1, term._right_most - rand_x)
        self._check_zero(['a'] * rand_len, (rand_x, rand_y))

    def test_scroll_up(self):
        """The terminal should have the possibility to move an area by
        1 line up.
        """
        term = self._terminal

        self._check_scroll_up(['f'] * term._cols, (0, 1))

        rand_y = random.randint(2, term._bottom_most - 1)
        self._check_scroll_up(['r'] * term._cols, (0, rand_y))

        # TODO: add a test case for checking scrolling up the last line.

    def test_scroll_down(self):
        """The terminal should have the possibility to move an area by
        1 line down.
        """
        term = self._terminal

        self._check_scroll_down(['f'] * term._right_most, (0, 0))
        self._check_scroll_down(['l'] * term._right_most,
                                (0, term._bottom_most - 1))

        rand_y = random.randint(2, term._bottom_most - 2)
        self._check_scroll_down(['r'] * term._right_most, (0, rand_y))

    def test_scroll_right(self):
        """The terminal should have the possibility to move an area by
        1 position right.
        """
        term = self._terminal

        self._check_scroll_right('test', (0, 0))

        s = 'test'
        self._check_scroll_right(s,
                                 (random.randint(1, term._right_most - len(s)),
                                  random.randint(1, term._bottom_most)))

    def test_peek(self):
        """The terminal should have the possibility to capture the area of the
        screen from a left border starting at position x1, y1 to a right border
        starting at position x2, y2.
        """
        term = self._terminal

        self._check_peek(['s'] * term._right_most, (0, 0))
        self._check_peek(['s'] * term._right_most, (0, term._bottom_most))

        rand_y = random.randint(1, term._bottom_most - 1)
        self._check_peek(['s'] * term._right_most, (0, rand_y))

    def test_peek_inclusively(self):
        """The terminal should have the possibility to capture the area of the
        screen from a left border starting at position x1, y1 to a right border
        starting at position x2, y2 inclusive.
        """
        term = self._terminal

        start = 3
        end = 7
        zeros = array.array('Q', [0] * (end - start))

        # The last '0' will be on the 6th position.
        term._screen[start:end] = zeros

        # Get an area from the 3rd to the 6th character.
        got = term._peek((start, 0), (end, 0))
        self.assertEqual(zeros, got)

        # Get an area from the 3rd to the 7th character.
        got = term._peek((start, 0), (end, 0), inclusively=True)
        zeros.append(BLACK_AND_WHITE)
        self.assertEqual(zeros, got)

    def test_poke(self):
        """The terminal should have the possibility to put the specified slice
        on the screen staring at the specified position.
        """
        term = self._terminal
        zeros = array.array('Q', [0] * term._right_most)

        self._check_poke(zeros, (0, 0))

        rand_y = random.randint(1, term._bottom_most - 1)
        self._check_poke(zeros, (0, rand_y))

        self._check_poke(zeros, (0, term._bottom_most))

    def test_cap_blink(self):
        """The terminal should have the possibility to produce blinking text.
        """
        term = self._terminal
        term._cap_blink()
        self.assertTrue(term._is_bit_set(BLINK_BIT, term._sgr))

    def test_cap_bold(self):
        """The terminal should have the possibility to produce bold text. """
        term = self._terminal
        term._cap_bold()
        self.assertTrue(term._is_bit_set(BOLD_BIT, term._sgr))

    def test_cap_cub1(self):
        """The terminal should have the possibility to move the cursor left by
        1 position.
        """
        self._check_cap_cub1((0, 0))
        self._check_cap_cub1((1, 0))
        self._check_cap_cub1((self._terminal._right_most, 0))

        rand_x = random.randint(2, self._terminal._right_most - 1)
        self._check_cap_cub1((rand_x, 0))

    def test_cap_cr(self):
        """The terminal should have the possibility to do carriage return. """
        self._check_cap_cr((0, 0))
        self._check_cap_cr((self._terminal._right_most, 0))
        self._check_cap_cr((random.randint(1, self._terminal._right_most), 0))

    def test_cap_csr(self):
        """ The terminal should have the possibility to change the scrolling
        region.
        """
        self._check_cap_csr((1, 1))
        self._check_cap_csr((1, 2))
        self._check_cap_csr((2, 1))

        rand_top = random.randint(2, self._rows - 1)
        rand_bottom = random.randint(2, self._rows - 1)
        self._check_cap_csr((rand_top, rand_bottom))

        self._check_cap_csr((self._rows, self._rows))

    def test_cap_cuf(self):
        """The terminal should have the possibility to move the cursor right by
        a specified number of positions.
        """
        term = self._terminal

        # Move the cursor to the right-most position.
        term._cap_cuf(term._right_most)
        self.assertEqual(term._cur_x, term._right_most)
        self.assertFalse(term._eol)

        # Then move the cursor right by 1 position to check reaching the end of
        # the line.
        term._cap_cuf(1)
        self.assertTrue(term._eol)

    def test_cap_cup(self):
        """The terminal should have the possibility to set the vertical and
        horizontal positions of the cursor to the specified values.
        """
        term = self._terminal

        # The cursor is at the left-most position.
        # Note that the y and x values start from 1.
        self._check_cap_cup((1, 1))
        self._check_cap_cup((term._cols, term._rows))

        rand_x = random.randint(1, term._right_most - 1)
        rand_y = random.randint(1, term._bottom_most - 1)
        self._check_cap_cup((rand_x, rand_y))

    def test_cap_dch(self):
        """The terminal should have the possibility to delete the specified
        number of characters.
        """
        term = self._terminal

        greeting = 'Hello, World!'
        self._check_cap_dch(greeting, 7)  # remove 'Hello, '

        self._check_cap_dch(greeting, 0)
        self._check_cap_dch(['a'] * term._right_most, term._right_most)
        self._check_cap_dch(['b'] * term._cols, term._cols)

        # Remove a character.

        s = self._get_random_string(term._cols)
        self._put_string(s, (0, 0))
        self._check_string(s, (0, 0), (len(s), 0))

        term._cur_x = random.randint(0, term._right_most)
        term._cap_dch(1)

        want = s[:term._cur_x] + s[term._cur_x + 1:]
        self._check_string(want, (0, 0), (len(want), 0))

    def test_cap_dl(self):
        """The terminal should have the possibility to delete ``n`` number of
        lines.
        """
        term = self._terminal

        self._check_cap_dl(0, [(['f'] * term._cols, (0, 0))])
        self._check_cap_dl(1, [(['f'] * term._cols, (0, 0))])

        self._check_cap_dl(1, [
            (['t'] * term._cols, (0, 0)),
            (['a'] * term._cols, (0, 1)),
        ])

        self._check_cap_dl(2, [
            (['t'] * term._cols, (0, 0)),
            (['k'] * term._cols, (0, 1)),
        ])

        self._check_cap_dl(2, [
            (['f'] * term._cols, (0, 0)),
            (['s'] * term._cols, (0, 1)),
            (['k'] * term._cols, (0, 2)),
        ])

        self._check_cap_dl(1, [
            (['f'] * term._cols, (0, 0)),
            (['s'] * term._cols, (0, 1)),
            (['k'] * term._cols, (0, 2)),
        ])

        self._check_cap_dl(0, [
            (['f'] * term._cols, (0, 0)),
            (['s'] * term._cols, (0, 1)),
            (['k'] * term._cols, (0, 2)),
        ])

        lines_number = random.randint(2, term._bottom_most)
        lines = []
        for i in range(lines_number):
            lines.append((['a'] * term._cols, (0, i)))

        self._check_cap_dl(random.randint(0, lines_number), lines)

    def test_cap_ech(self):
        """The terminal should have the possibility to erase the specified
        number of characters.
        """
        term = self._terminal

        self._check_cap_ech(['a'] * term._right_most, (0, 0), 0)
        self._check_cap_ech(['a'] * term._right_most, (0, 0), term._right_most)

        rand_x = random.randint(1, term._right_most - 1)
        self._check_cap_ech(['a'] * term._right_most, (0, 0), rand_x)

    def test_cap_ed(self):
        """The terminal should have the possibility to clear the screen from
        the current cursor position to the end of the screen.
        """
        term = self._terminal

        prompt = 'spam@ham:~$ '
        self._put_string(prompt, (0, 0))
        self._check_string(prompt, (0, 0), (len(prompt), 0))

        # Fill the rest of the screen with x.
        length = term._cols * term._rows - len(prompt)
        self._put_string(['x'] * length, (len(prompt), 0))

        # Clear the screen after the prompt till the end of the screen.
        term._cur_x = len(prompt)
        term._cur_y = 0
        term._cap_ed()

        # Check that the prompt was not corrupted.
        self._check_string(prompt, (0, 0), (len(prompt), 0))

        # Check that the screen was cleared correctly.
        want = array.array('Q', [BLACK_AND_WHITE] * length)
        got = term._peek((term._cur_x, 0),
                         (term._right_most, term._bottom_most),
                         inclusively=True)
        self.assertEqual(want, got)

    def test_cap_el(self):
        """The terminal should have the possibility to clear a line from the
        current cursor position to the end of the line.
        """
        term = self._terminal

        self._check_cap_el(['s'] * term._right_most, (0, 0))
        self._check_cap_el(['s'] * term._right_most, (term._right_most, 0))

        rand_x = random.randint(1, term._right_most - 1)
        self._check_cap_el(['s'] * term._right_most, (rand_x, 0))

    def test_cap_el1(self):
        """The terminal should have the possibility to clear a line from the
        beginning to the current cursor position.
        """
        term = self._terminal

        self._check_cap_el1(['s'] * term._right_most, (0, 0))
        self._check_cap_el1(['s'] * term._right_most, (term._right_most, 0))

        rand_x = random.randint(1, term._right_most - 1)
        self._check_cap_el1(['s'] * term._right_most, (rand_x, 0))

    def test_cap_home(self):
        """The terminal should have the possibility to move the cursor to the
        home position.
        """
        term = self._terminal

        self._check_cap_home((0, 0))

        # The x position of the cursor is at the right-most position and
        # the end of the line was reached.
        self._put_string(['t'] * term._right_most, (0, 0))
        self._check_cap_home((term._right_most, term._bottom_most))

        rand_x = random.randint(1, term._right_most - 1)
        rand_y = random.randint(1, term._bottom_most - 1)
        self._check_cap_home((rand_x, rand_y))

    def test_cap_hpa(self):
        """The terminal should have the possibility to set the horizontal
        position to the specified value.
        """
        term = self._terminal

        self._check_cap_hpa(1)
        self._check_cap_hpa(term._cols)

        rand_x = random.randint(2, term._cols - 1)
        self._check_cap_hpa(rand_x)

    def test_cap_ht(self):
        """The terminal should have the possibility to tab to the next 8-space
        hardware tab stop.
        """
        term = self._terminal
        tab = 8

        # echo -e "\tHello"
        s = 'Hello'
        term._cap_ht()
        self._put_string(s, (term._cur_x, 0))
        # There must be 8 spaces at the beginning of the line.
        want = ('\x00' * tab) + s
        self._check_string(want, (0, 0), (len(s) + tab, 0))
        term._cap_rs1()

        # echo -e "Hello,\tWorld!"
        part1, part2 = 'Hello,', 'World!'
        self._put_string(part1, (0, 0))
        term._cap_ht()
        self._put_string(part2, (term._cur_x, 0))
        spaces = tab - len(part1)
        # There must be 2 spaces between 'Hello,' and 'World!' because 'Hello,'
        # consists of 6 characters (tab - 6 = 2).
        self.assertEqual(2, spaces)
        want = part1 + ('\x00' * spaces) + part2
        self._check_string(want, (0, 0), (len(want), 0))
        term._cap_rs1()

        # echo -e "Buzzword\tcontains 8 letters"
        part1, part2 = 'Buzzword', 'contains 8 letters'
        self._put_string(part1, (0, 0))
        term._cap_ht()
        self._put_string(part2, (term._cur_x, 0))
        # There must be 8 spaces between 'Buzzword' and 'contains 8 letters'
        # because 'Buzzword' consists of 8 characters.
        want = part1 + ('\x00' * tab) + part2
        self._check_string(want, (0, 0), (len(want), 0))

    def test_cap_ich(self):
        """The terminal should have the possibility to insert the specified
        number of blank characters.
        """
        term = self._terminal

        self._put_string(['x'] * self._cols, (0, 0))
        term._cur_x = term._cur_y = 0

        n = random.randint(0, term._right_most)
        # Insert n blank characters at the beginning of the first line.
        term._cap_ich(n)

        blank_characters = ['\x00'] * n
        want = blank_characters + ['x'] * (self._cols - n)
        self._check_string(want, (0, 0), (term._cols, 0))

    def test_cap_il1(self):
        """The terminal should have the possibility to add a new blank line.
        """
        term = self._terminal

        self._check_cap_il1(['s'] * term._right_most, (0, 0))
        self._check_cap_il1(['s'] * term._right_most, (0, term._bottom_most))

        rand_y = random.randint(1, term._bottom_most - 1)
        self._check_cap_il1(['s'] * term._right_most, (0, rand_y))

    def test_cap_ind(self):
        """The terminal should have the possibility to move the cursor down by
        1 position.
        """
        self._terminal._cap_ind()
        self.assertEqual(1, self._terminal._cur_y)

    def test_cap_kcub1(self):
        """The terminal should have the possibility to handle a Left Arrow
        key-press.
        """
        term = self._terminal

        self._check_cap_kcub1((0, 0))
        self._check_cap_kcub1((1, 0))
        self._check_cap_kcub1((term._right_most, 0))

        rand_x = random.randint(2, term._right_most - 1)
        self._check_cap_kcub1((rand_x, 0))

    def test_cap_kcud1(self):
        """The terminal should have the possibility to handle a Down Arrow
        key-press.
        """
        term = self._terminal

        self._check_cap_kcud1((0, 0), want_cur_y=1)
        self._check_cap_kcud1((0, term._bottom_most),
                              want_cur_y=term._bottom_most)

        rand_y = random.randint(1, term._bottom_most - 1)
        self._check_cap_kcud1((0, rand_y), want_cur_y=rand_y + 1)

    def test_cap_kcuu1(self):
        """The terminal should have the possibility to handle an Up Arrow
        key-press.
        """
        term = self._terminal

        self._check_cap_kcuu1((0, 0), term._top_most)
        self._check_cap_kcuu1((0, term._bottom_most), term._bottom_most - 1)

        rand_y = random.randint(1, term._bottom_most - 1)
        self._check_cap_kcuu1((0, rand_y), rand_y - 1)

    def test_cap_op(self):
        """The terminal should have the possibility to set default color-pair
        to the original one.
        """
        self._terminal._sgr = None
        self._terminal._cap_op()
        self.assertEqual(BLACK_AND_WHITE, self._terminal._sgr)

    def test_cap_rc(self):
        """The terminal should have the possibility to restore the cursor to
        the last saved position.
        """
        term = self._terminal
        term._cur_x = term._right_most - 1

        # Put a character to move the cursor to the right-most position.
        term._echo('e')

        # After putting another character we will reach the end of the line.
        term._echo('g')
        self.assertTrue(term._eol)

        cur_x_bck = term._cur_x
        term._cap_sc()  # save the cursor current position.

        # Put one more character to move the cursor to the next line.
        term._echo('g')

        term._cap_rc()  # restore a previously saved cursor position.
        self.assertEqual(cur_x_bck, term._cur_x)
        self.assertTrue(term._eol)

    def test_cap_rev(self):
        term = self._terminal
        term._cap_rev()
        self.assertTrue(term._is_bit_set(REVERSE_BIT, term._sgr))

    def test_cap_ri(self):
        """The terminal should have the possibility to scroll text down. """
        term = self._terminal

        self._check_cap_ri(['x'] * term._right_most, (0, 0))
        self._check_cap_ri(['x'] * term._right_most, (0, 1))

        rand_y = random.randint(2, term._bottom_most)
        self._check_cap_ri(['x'] * term._right_most, (0, rand_y))

    def test_cap_rs1(self):
        """The terminal should have the possibility to completely reset to sane
        modes.
        """
        # Do some useless work.
        self._terminal._echo('a')
        self._terminal._cursor_right()
        self._terminal._cursor_down()
        self._terminal._scroll_down(0, self._terminal._bottom_most)

        # Reset the terminal to sane modes.
        self._terminal._cap_rs1()
        self.assertEqual(0, self._terminal._cur_x)
        self.assertEqual(0, self._terminal._cur_y)
        self.assertFalse(self._terminal._eol)

    def test_cap_sc(self):
        """The terminal should have the possibility to save the current cursor
        position.
        """
        term = self._terminal
        x = random.randint(0, term._right_most)
        y = random.randint(0, term._bottom_most)
        term._cur_x, term._cur_y = x, y
        term._cap_sc()

        self.assertEqual(x, term._cur_x_bak)
        self.assertEqual(y, term._cur_y_bak)

    def test_cap_sgr0(self):
        """The terminal should have the possibility to turn off all attributes.
        """
        self._terminal._sgr = None
        self._terminal._cap_sgr0()
        self.assertEqual(BLACK_AND_WHITE, self._terminal._sgr)

    def test_cap_smso(self):
        """The terminal should have the possibility to enter Standout mode. """
        pass

    def test_cap_smul_rmul(self):
        """The terminal should have the possibility to enter and exit
        Underline mode.
        """
        term = self._terminal
        term._cap_smul()
        self.assertTrue(term._is_bit_set(UNDERLINE_BIT, term._sgr))
        term._cap_rmul()
        self.assertFalse(term._is_bit_set(UNDERLINE_BIT, term._sgr))

    def test_cap_vpa(self):
        """The terminal should have the possibility to set the vertical
        position of the cursor to the specified value.
        """
        term = self._terminal

        self._check_cap_vpa(1)
        self._check_cap_vpa(term._rows)

        rand_y = random.randint(1, term._rows - 1)
        self._check_cap_vpa(rand_y)

if __name__ == '__main__':
    unittest.main()
