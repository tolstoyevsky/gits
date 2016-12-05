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
        """A helper function that checks if screen has the string ``s`` from
        ``left_border`` to ``right_border``.
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

    def _check_echo(self, c, pos, eol=False, down=False):
        """A helper function that checks the `echo` command.

        The ``pos`` argument must be a tuple or list of coordinates ``(x, y)``.
        ``c`` represents a character that screen will have on the
        position ``pos``.
        """

        if len(pos) != 2:
            self.fail("`pos` must have x and y as cursor's coordinates.")

        term = self._terminal
        term._eol = False

        cur_x, cur_y = term._cur_x, term._cur_y = pos

        term.echo(c)

        if eol:
            # EOL (end of line) was reached, cur_x position must no be changed.
            self.assertTrue(term._eol)
            self.assertEqual(cur_x, term._cur_x)
            check_screen_pos = (term._cur_y * term._cols) + term._cur_x
        else:
            # EOL (end of line) was not reached, cur_x was moved right by 1
            # position.
            self.assertFalse(term._eol)
            self.assertEqual(cur_x + 1, term._cur_x)
            check_screen_pos = (term._cur_y * term._cols) + (term._cur_x - 1)

        if down:
            term.echo(c)
            self.assertEqual(cur_y + 1, term._cur_y)
            self.assertEqual(1, term._cur_x)
            self.assertFalse(term._eol)
        else:
            self.assertEqual(cur_y, term._cur_y)

        # Check if the screen has the correct character on the
        # corresponding position.
        self._check_screen_char(c, check_screen_pos)

    def _check_zero(self, s, pos):
        """A helper function that checks the cleaning of the screen.

        ``s`` defines a string that will be cleared from the screen.
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

    def test_cursor_right(self):
        """Emulator should move cursor right by 1 position."""

        # Cursor is one the most left position.
        self._check_cursor_right(0)

        # Cursor is one an arbitrary position.
        rand_x = random.randint(1, self._cols - 2)
        self._check_cursor_right(rand_x)

        # Cursor is one the most right position.
        self._check_cursor_right(self._cols - 1, eol=True)

    def test_cursor_down(self):
        """Emulator should move cursor down by 1 position."""

        # Cursor is on the most top position.
        self._check_cursor_down(0)

        # Cursor is one an arbitrary position.
        rand_y = random.randint(1, self._rows - 2)
        self._check_cursor_down(rand_y)

        # Cursor is one the most down position.
        self._check_cursor_down(self._cols - 1, top=True)

    def test_echo(self):
        """Emulator should put the specified character ``c`` on the screen and
        move cursor right by one position.
        """

        # Echo the character on the screen (most left corner).
        self._check_echo('d', (0, 0))

        # Echo the character on an arbitrary position on the screen.
        rand_cur_x = random.randint(1, self._cols - 2)
        rand_cur_y = random.randint(1, self._rows - 2)
        self._check_echo('r', (rand_cur_x, rand_cur_y))

        # Echo the character on the screen (most right position).
        self._check_echo('a', (self._cols - 1, rand_cur_y), eol=True)

        # EOL was reached earlier, echo one more character on the screen.
        self._check_echo('t', (self._cols - 1, rand_cur_y),
                         eol=True, down=True)

        # Echo the character on the screen (most right corner).
        self._check_echo('p', (self._cols - 1, self._rows - 1), eol=True)

    def test_zero(self):
        """Emulator should clear the area from left to right."""

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
        """Emulator should move area one line up."""

        stub = array.array('L', [MAGIC_NUMBER] * self._terminal._cols)
        # Clear the whole second line
        self._terminal.poke((0, 1), stub)
        self._terminal.scroll_up(1, self._terminal._rows)
        # Check that after scrolling up the line moved up one position
        line = self._terminal.peek((0, 0), (len(stub), 0))
        self.assertEqual(stub, line)

    @unittest.skip("skip")
    def test_scroll_down(self):
        """Emulator should move area by one line down."""
        pass

    @unittest.skip("skip")
    def test_scroll_right(self):
        """Emulator should move area by one position right."""
        pass

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
