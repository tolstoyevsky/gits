#!/usr/bin/python3
import array
import unittest

from terminal import Terminal, MAGIC_NUMBER


class TestEmulator(unittest.TestCase):
    def setUp(self):
        self._rows = 24
        self._cols = 80
        self._terminal = Terminal(self._rows, self._cols)

    def _put_string(self, s):
        for character in s:
            self._terminal.echo(character)

    def _check_string(self, s, left_border, right_border):
        x1, y1 = left_border
        x2, y2 = right_border

        got = array.array('L', [])
        for c in s:
            got.append(self._terminal._sgr | ord(c))

        self.assertEqual(self._terminal.peek((x1, y1), (x2, y2)), got)

    def _check_screen_char(self, c, pos):
        """A helper function that checks if the screen has the character ``c``
        on the corresponding position ``pos``.
        """

        term = self._terminal
        want = term._sgr | ord(c)
        got = term._screen[pos]
        self.assertEqual(want, got)

    def test_cursor_right(self):
        """Emulator should move cursor right by 1 position."""

        # Test the most left position.
        self._terminal._cur_x = 0
        self._terminal.cursor_right()

        self.assertFalse(self._terminal._eol)
        self.assertEqual(1, self._terminal._cur_x)

        # Existing tests cover the cases when cursor is on the most right
        # position.
        #
        # These positions will never be achieved, because if cursor is on the
        # most right position - 1 then the next position will be equal to
        # the number of columns in the emulator and EOL (end of line) will be
        # reached and the cursor position will not be changed.

        # Test the most right position - 1
        self._terminal._cur_x = self._cols - 1
        self._terminal.cursor_right()

        # Cursor is on the most right position - 1. Its position must not be
        # changed.
        self.assertTrue(self._terminal._eol)
        self.assertEqual(self._cols - 1, self._terminal._cur_x)

        # Test the most right position.
        self._terminal._eol = False
        self._terminal._cur_x = self._cols
        self._terminal.cursor_right()

        # Cursor is on the most right position. Its position must not be
        # changed.
        self.assertTrue(self._terminal._eol)
        self.assertEqual(self._terminal._cols, self._terminal._cur_x)

    def test_cursor_down(self):
        """Emulator should move cursor down by 1 position."""

        self._terminal._cur_y = 0
        self._terminal.cursor_down()

        self.assertEqual(1, self._terminal._cur_y)

        # Existing tests cover the cases when cursor is on the most down
        # position.
        #
        # These positions will never be achieved, because if cursor is on the
        # most down position - 1 then the next position will be equal to the
        # number of rows in the emulator and the cursor position will not be
        # changed.

        # Test most down position - 1
        self._terminal._cur_y = self._rows - 1
        self._terminal.cursor_down()

        # Cursor is on the most down position - 1. Its position must not be
        # changed.
        self.assertEqual(self._rows - 1, self._terminal._cur_y)

        # Test most down position
        self._terminal._cur_y = self._rows
        self._terminal.cursor_down()

        # Cursor is on the most down position. Its position must not be
        # changed.
        self.assertEqual(self._rows, self._terminal._cur_y)

    def test_echo(self):
        """Emulator should put the specified character ``c`` on the screen and
        move cursor right by one position.
        """

        c = 'd'
        term = self._terminal

        term._cur_x = 1
        term._cur_y = 1
        term.echo(c)

        # Check the correctness or cursor right shift.
        self.assertEqual(2, term._cur_x)

        # Check if the screen has the correct character on the corresponding
        # position.
        self._check_screen_char(
            c,
            (term._cur_y * term._cols) + (term._cur_x - 1)
        )

    def test_echo_eol(self):
        """Emulator should put specified character ``c`` on the screen and move
        cursor down by one position if cursor reaches the end of line.
        """

        term = self._terminal
        term._eol = False

        # Put the cursor on the right most position - 1.
        term._cur_x = term._cols - 1
        term._cur_y = 1
        term.echo('d')

        # The end of line was reached, eol must be True.
        # x position of cursor must not be changed.
        self.assertTrue(term._eol)
        self.assertEqual(term._cols - 1, term._cur_x)

        # Check if the screen has the correct character on the corresponding
        # position.
        self._check_screen_char(
            'd',
            (term._cur_y * term._cols) + term._cur_x
        )

        # Echo one more character. EOL was reached, that's why cursor must be
        # moved down by one position.
        term.echo('a')
        self.assertEqual(1, term._cur_x)
        self.assertFalse(term._eol)
        self.assertEqual(2, term._cur_y)

        # Check if the screen has the correct character on the corresponding
        # position.
        self._check_screen_char(
            'a',
            (term._cur_y * term._cols) + (term._cur_x - 1)
        )

    def test_zero(self):
        """Emulator should clear the area from left to right."""

        # Clear the first five lines (from 0 to 4)
        length = self._terminal.zero((0, 0), (0, 4))
        area = self._terminal.peek((0, 0), (0, 4))
        self.assertEqual(length, len(area) + 1)

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
        self._put_string(prompt)  # put a prompt on the screen

        # Check that the prompt was put correctly
        self._check_string(prompt, (0, 0), (len(prompt), 0))

        # Fill the rest of the screen with x
        length = term._cols * term._rows - len(prompt)
        self._put_string(['x'] * length)

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
