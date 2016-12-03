#!/usr/bin/python3
import array
import unittest

from terminal import Terminal, MAGIC_NUMBER


class TestEmulator(unittest.TestCase):
    def setUp(self):
        self._rows = 24
        self._cols = 80
        self._terminal = Terminal(self._rows, self._cols)

    def check_screen_char(self, c, pos):
        """A helper function that checks if screen has the character ``c`` on the
        corresponding position ``pos``.
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
        self.assertEqual(self._terminal._cur_x, 1)

        # Test the most right position - 1
        self._terminal._cur_x = self._cols - 1
        self._terminal.cursor_right()
        
        # Cursor is on the most right position - 1. It position must no be changed.
        self.assertTrue(self._terminal._eol)
        self.assertEqual(self._terminal._cur_x, self._cols - 1)

        # Test the most right position.
        self._terminal._eol = False
        self._terminal._cur_x = self._cols
        self._terminal.cursor_right()
        
        # Cursor is on the most right position. It position must no be changed.
        self.assertTrue(self._terminal._eol)
        self.assertEqual(self._terminal._cols, self._terminal._cur_x)

    def test_cursor_down(self):
        """Emulator should move cursor down by 1 position."""

        self._terminal._cur_y = 0
        self._terminal.cursor_down()

        self.assertEqual(self._terminal._cur_y, 1)

        # Test most down position - 1
        self._terminal._cur_y = self._rows - 1
        self._terminal.cursor_down()

        # Cursor is on the most down position -1. It position must no be changed.
        self.assertEqual(self._terminal._cur_y, self._rows - 1)

        # Test most down position
        self._terminal._cur_y = self._rows
        self._terminal.cursor_down()

        # Cursor is on the most down position. It position must no be changed.
        self.assertEqual(self._terminal._cur_y, self._rows)

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

        # Check if screen has the correct character on the corresponding position.
        self.check_screen_char(
            c, 
            (term._cur_y * term._cols) + (term._cur_x - 1)
        )

    def test_echo_eol(self):
        """Emulator should put specified character ``c`` on the screen and move 
        cursor down by one position if cursor reaches the end of line.
        """
        
        term = self._terminal
        term._eol = False

        # put the cursor on the right most position - 1.
        term._cur_x = term._cols - 1
        term._cur_y = 1
        term.echo('d')

        # The end of line was reached, eol must be True.
        # x position of cursor must not be changed.
        self.assertTrue(term._eol)
        self.assertEqual(term._cols - 1, term._cur_x)

        # Check if screen has the correct character on the corresponding position.
        self.check_screen_char(
            'd',
            (term._cur_y * term._cols) + term._cur_x
        )

        # Echo one more character. EOL was reached, that's why cursor must be 
        # moved down by one position.
        term.echo('a')
        self.assertEqual(1, term._cur_x)
        self.assertFalse(term._eol)
        self.assertEqual(2, term._cur_y)

        # Check if screen has the correct character on the corresponding position.
        self.check_screen_char(
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

if __name__ == '__main__':
    unittest.main()
