import unittest

from debug_log import debug_log


class DebugLogTest(unittest.TestCase):
    def test_should_log_debug_info_with_debug_log_decorator(self):

        @debug_log
        def do_something(*args, **kwargs):
            print('did something for len(args)={}, len(kwargs)={}'.format(len(args), len(kwargs)))
            return len(args), len(kwargs)

        args_len, kwargs_len = do_something(1, 2, a=3, b=4)
        self.assertEquals(args_len, 2)
        self.assertEquals(kwargs_len, 2)


if __name__ == '__main__':
    unittest.main()
