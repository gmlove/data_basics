import unittest

from rect import Rect


class RectTest(unittest.TestCase):
    def test_intersect_for_crossing_rects(self):
        self.assertTrue(Rect(1, 1, 1, 1).intersect(Rect(1, 1, 0.5, 0.5)))


if __name__ == '__main__':
    unittest.main()
