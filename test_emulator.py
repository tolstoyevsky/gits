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
        """A helper function that puts the string ``s`` to the screen
        beginning from the position ``pos``.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        """

        self._terminal._cur_x, self._terminal._cur_y = pos
        for character in s:
            self._terminal.echo(character)

    def _check_string(self, s, left_border, right_border):
        """A helper function that checks if the screen has the string ``s``
        with a left border starting at position x1, yx, and a right border
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
        """A helper function that checks the cursor right shift."""

        self._terminal._cur_x = cur_x
        self._terminal.cursor_right()

        if eol:
            self.assertTrue(self._terminal._eol)
            self.assertEqual(cur_x, self._terminal._cur_x)
        else:
            self.assertFalse(self._terminal._eol)
            self.assertEqual(cur_x + 1, self._terminal._cur_x)

    def _check_cursor_down(self, cur_y, top=False):
        """A helper function that checks the cursor down shift."""

        self._terminal._cur_y = cur_y
        self._terminal.cursor_down()

        if top:
            self.assertEqual(cur_y, self._terminal._cur_y)
        else:
            self.assertEqual(cur_y + 1, self._terminal._cur_y)

    def _check_echo(self, c, pos, eol=False):
        """A helper function that checks the `echo` method.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        The ``c`` argument is a character that screen will have on the position
        ``pos``.
        Set ``eol`` to True if you expect that after calling the `echo` method
        cursor must be at the end of a line.
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
        """A helper function that checks the cleaning of the screen.

        The ``s`` argument defines a string that will be cleared from the
        screen.
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
        """A helper function that checks the screen scrolling up.

        The ``s`` argument is a test string putting on the screen.
        The ``pos`` argument is a tuple or list of coordinates ``(x, y)``.
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
        """A helper function that checks the screen scrolling down.

        The ``s`` argument is a test string putting on the screen.
        The ``pos`` argument is a tuple or list of coordinates ``(x, y)``.
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
        rand_y = random.randint(1, self._rows - 2)
        self._check_cursor_down(rand_y)

        # Cursor is on the down-most position.
        self._check_cursor_down(self._cols - 1, top=True)

    def test_echo(self):
        """The terminal should put the specified character ``c`` on the screen
        and move the cursor right by one position.
        """

        # Echo the character on the screen (left-most position).
        self._check_echo('d', (0, 0))

        # Echo the character on an arbitrary position on the screen.
        rand_cur_x = random.randint(1, self._cols - 2)
        rand_cur_y = random.randint(1, self._rows - 2)
        self._check_echo('r', (rand_cur_x, rand_cur_y))

        # Echo the character on the screen (right-most position).
        self._check_echo('a', (self._cols - 1, rand_cur_y), eol=True)

        # Echo the character on the screen (right-most position).
        self._check_echo('p', (self._cols - 1, self._rows - 1), eol=True)

    def test_echo_eol(self):
        term = self._terminal

        term._cur_x = term._cols - 2  # the next to the last position

        term.echo('e')  # moves the cursor to the right-most position
        term.echo('g')  # puts a new character and sets eol to True
        self.assertTrue(term._eol)

        term.echo('g')  # puts a new character on the next line
        self.assertEqual(1, term._cur_x)
        self.assertEqual(1, term._cur_y)
        self.assertFalse(term._eol)

    def test_zero(self):
        """The terminal should clear the area from left to right."""

        # Clear first line.
        self._check_zero(["a"] * (self._cols - 1), (0, 0))

        # Clear last line.
        self._check_zero(["z"] * (self._cols - 1), (0, self._rows - 1))

        # Clear random number of line.
        rand_x = random.randint(1, self._cols - 2)
        rand_y = random.randint(1, self._rows - 2)
        rand_len = random.randint(1, (self._cols - 1) - rand_x)
        self._check_zero(["p"] * rand_len, (rand_x, rand_y))

        # Clear the whole screen.
        self._check_zero(["w"] * (self._cols - 1) * (self._rows - 1), (0, 0))

    def test_scroll_up(self):
        """The terminal should move area by one line up."""

        term = self._terminal

        # Scroll up the first line.
        self._check_scroll_up(['f'] * (self._cols - 1), (0, 1))

        # Scroll up the last line.
        self._check_scroll_up(['l'] * (self._cols - 1), (0, term._bottom))

        # Scroll up the random line.
        rand_y = random.randint(2, term._bottom - 1)
        self._check_scroll_up(['r'] * (self._cols - 1), (0, rand_y))

    def test_scroll_down(self):
        """The terminal should move area by one line down."""

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
        """The terminal should move area by one position right."""
        pass

    def test_peek(self):
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
        self.assertEqual(zeros + array.array('L', [MAGIC_NUMBER]), got)

    def test_poke(self):
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
        got = term.peek((term._cur_x, 0), (term._cols - 1, term._rows - 1),
                        inclusively=True)
        self.assertEqual(want, got)


if __name__ == '__main__':
    unittest.main()
