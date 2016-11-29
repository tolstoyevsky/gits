#!/usr/bin/python3
import array
import unittest
import sys

from terminal import Terminal, MAGIC_NUMBER


class TestEmulator(unittest.TestCase):
    def setUp(self):
        self._rows = 24
        self._cols = 80
        self._terminal = Terminal(self._rows, self._cols)

    def test_cursor_right(self):
        """Emulator should move cursor right by 1 position."""

        self._terminal._cur_x = 0
        self._terminal.cursor_right()

        self.assertEqual(self._terminal._cur_x, 1)

        # test the most right position
        self._terminal._cur_x = self._cols
        self._terminal.cursor_right()

        # because cursor is on the most right position
        # it position must no be changed.
        self.assertEqual(self._terminal._cur_x, self._cols)

    def test_cursor_down(self):
        """Emulator should move cursor down by 1 position."""

        self._terminal._cur_y = 0
        self._terminal.cursor_down()

        self.assertEqual(self._terminal._cur_y, 1)

        # test most down position
        self._terminal._cur_y = self._rows
        self._terminal.cursor_down()

        # because cursor is on the most down position
        # it position must no be changed.
        self.assertEqual(self._terminal._cur_y, self._rows)

    @unittest.skip("skip")
    def test_echo(self):
        """
        Emulator should write to standard output destination
        any specified operands.
        """
        pass

    def test_zero(self):
        """Emulator should clear the area from left to right."""

        # Clear the first five lines (from 0 to 4)
        length = self._terminal.zero((0, 0), (0, 4))
        area = self._terminal.peek((0, 0), (0, 4))
        self.assertEqual(length, len(area) + 1)

    def test_scroll_up(self):
        """Emulator should move are one line up."""

        stub = array.array('L', [MAGIC_NUMBER] * self._terminal._cols)
        # Clear the whole second line
        self._terminal.poke((0, 1), stub)
        self._terminal.scroll_up(1, self._terminal._rows)
        # Check that after scrolling up the line moved up one position
        line = self._terminal.peek((0, 0), (len(stub), 0))
        self.assertEqual(stub, line)

    @unittest.skip("skip")
    def test_scroll_down(self):
        """Emulator should move area one line down."""
        pass

    @unittest.skip("skip")
    def test_scroll_right(self):
        """Emulator should move area to 1 position right."""
        pass

if __name__ == '__main__':
    unittest.main()
