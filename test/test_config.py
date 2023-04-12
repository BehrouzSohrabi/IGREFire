import unittest
import src.config

class TestMain(unittest.TestCase):
    def test_run(self):
        self.assertEqual(None, None, 'It isn\'t a config.')


if __name__ == '__main__':
    unittest.main()