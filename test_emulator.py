#!/usr/bin/python3
import array
import unittest

from terminal import Terminal


class TestEmulator(unittest.TestCase):
    def setUp(self):
        self._rows = 24
        self._cols = 80
        self._terminal = Terminal(self._rows, self._cols)

    def test_cursor_right(self):
        self._terminal._cur_x = 0
        self._terminal.cursor_right()
        self.assertEqual(self._terminal._cur_x, 1)
        self._terminal._cur_x = self._cols
        self._terminal.cursor_right()
        self.assertEqual(self._terminal._cur_x, self._cols)

    def test_scroll_up(self):
        stub = array.array('L', [0x07000000] * self._terminal._cols)
        # Clear the whole second line
        self._terminal.poke((0, 1), stub)
        self._terminal.scroll_up(1, self._terminal._rows)
        # Check that after scrolling up the line moved up one position
        line = self._terminal.peek((0, 0), (len(stub), 0))
        self.assertEqual(stub, line)

    def test_zero(self):
        # Clear the first five lines (from 0 to 4)
        length = self._terminal.zero((0, 0), (0, 4))
        area = self._terminal.peek((0, 0), (0, 4))
        self.assertEqual(length, len(area) + 1)


if __name__ == '__main__':
    unittest.main()
