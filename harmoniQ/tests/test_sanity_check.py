import unittest
from harmoniq.utils import VERSION

class TestHelloWorld(unittest.TestCase):
    def test_hello_world(self):
        self.assertEqual("Hello, World!", "Hello, World!")

    def test_import_version(self):
        try:
            from harmoniq.utils import VERSION
        except ImportError:
            self.fail("Failed to import VERSION from harmoniq.utils")

if __name__ == '__main__':
    unittest.main()
