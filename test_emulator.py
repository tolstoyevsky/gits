#!/usr/bin/python3
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

        self.assertEqual(len(s) + 1, clear_len)

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
        self._check_string(s, pos, (self._cols - 1, y))

        # Scroll up the whole screen.
        term.scroll_up(0, term._bottom)

        self._check_string(s, (0, y - 1), (self._cols - 1, y - 1))

        want = array.array('L', [MAGIC_NUMBER] * (self._cols - 1))
        got = term.peek(pos, (self._cols - 1, y))
        self.assertEqual(want, got)

        # Restore the initial position of the screen.
        term.zero((0, 0), (self._cols - 1, term._bottom))

    def _check_scroll_down(self, s, pos):
        """A helper function that checks the `scroll_down` method.

        The ``s`` argument is a test string that will be put on the screen.
        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        """

        x, y = pos
        term = self._terminal

        self._put_string(s, pos)
        self._check_string(s, pos, (self._cols - 1, y))

        # Scroll down the whole screen.
        term.scroll_down(0, term._bottom)

        self._check_string(s, (0, y + 1), (self._cols - 1, y + 1))

        want = array.array('L', [MAGIC_NUMBER] * (self._cols - 1))
        got = term.peek(pos, (self._cols - 1, y))
        self.assertEqual(want, got)

        # Restore the initial position of the screen.
        term.zero((0, 0), (self._cols - 1, term._bottom))

    def test_cursor_right(self):
        """The terminal should move the cursor right by 1 position."""

        # Cursor is on the left-most position.
        self._check_cursor_right(0)

        # Cursor is on an arbitrary position.
        rand_x = random.randint(1, self._cols - 2)
        self._check_cursor_right(rand_x)

        # Cursor is on the right-most position.
        self._check_cursor_right(self._cols - 1, eol=True)

    def test_cursor_down(self):
        """The terminal should move the cursor down by 1 position."""

        # Cursor is on the top-most position.
        self._check_cursor_down(0)

        # Cursor is on an arbitrary position.
        rand_y = random.randint(1, self._terminal._bottom - 1)
        self._check_cursor_down(rand_y)

        # Cursor is on the down-most position.
        self._check_cursor_down(self._cols - 1, top=True)

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
        self._check_echo('a', (self._cols - 1, rand_cur_y), eol=True)

        # Echo the character on the screen (right-most position).
        self._check_echo('p', (self._cols - 1, term._bottom), eol=True)

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
        self._check_zero(['s'] * (self._cols - 1), (0, 0))

        # Clear the last line.
        self._check_zero(['p'] * (self._cols - 1), (0, term._bottom))

        # Clear a random number of lines.
        rand_x = random.randint(1, self._cols - 2)
        rand_y = random.randint(1, term._bottom - 1)
        rand_len = random.randint(1, (self._cols - 1) - rand_x)
        self._check_zero(['a'] * rand_len, (rand_x, rand_y))

        # Clear the whole screen.
        self._check_zero(['m'] * (self._cols - 1) * term._bottom, (0, 0))

    def test_scroll_up(self):
        """The terminal should move an area by 1 line up."""

        term = self._terminal

        # Scroll up the first line.
        self._check_scroll_up(['f'] * (self._cols - 1), (0, 1))

        # Scroll up the last line.
        self._check_scroll_up(['l'] * (self._cols - 1), (0, term._bottom))

        # Scroll up the random line.
        rand_y = random.randint(2, term._bottom - 1)
        self._check_scroll_up(['r'] * (self._cols - 1), (0, rand_y))

    def test_scroll_down(self):
        """The terminal should move an area by 1 line down."""

        term = self._terminal

        # Scroll down the first line.
        self._check_scroll_down(['f'] * (self._cols - 1), (0, 0))

        # Scroll down the last line.
        self._check_scroll_down(['l'] * (self._cols - 1), (0, term._bottom - 1))

        # Scroll down the random line.
        rand_y = random.randint(2, term._bottom - 2)
        self._check_scroll_down(['r'] * (self._cols - 1), (0, rand_y))

    @unittest.skip("skip")
    def test_scroll_right(self):
        """The terminal should move an area by 1 position right."""
        pass

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
        got = term.peek((term._cur_x, 0), (term._cols - 1, term._bottom),
                        inclusively=True)
        self.assertEqual(want, got)


if __name__ == '__main__':
    unittest.main()
