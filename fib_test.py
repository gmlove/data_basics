import unittest
from fib import fib


class FibTest(unittest.TestCase):
    def test_generate_5_fibs(self):
        self.assertEqual(fib(5), [1, 1, 2, 3, 5])

    def test_generate_10_fibs(self):
        pass

    def test_generate_negative_number_fibs(self):
        pass

    def test_generate_0_number_fibs(self):
        pass

    def test_generate_1_number_fibs(self):
        pass

    def test_generate_2_number_fibs(self):
        pass


if __name__ == '__main__':
    unittest.main()
