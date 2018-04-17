import unittest

import fastcat


class FastcatTests(unittest.TestCase):

    def test_narrower(self):
        f = fastcat.FastCat()
        f.load()
        self.assertTrue(f._is_loaded())
        self.assertTrue("Functional languages" in f.narrower("Functional programming"))

    def test_broader(self):
        f = fastcat.FastCat()
        f.load()
        self.assertTrue(f._is_loaded())
        self.assertTrue("Computing" in f.broader("Computer programming"))


class FastcatTestsPortuguese(unittest.TestCase):

    def test_narrower(self):
        f = fastcat.FastCat(language="pt")
        f.load()
        self.assertTrue(f._is_loaded())
        self.assertTrue("Linguagens de programação funcionais‎" in f.narrower("Programação_funcional"))

    def test_broader(self):
        f = fastcat.FastCat(language="pt")
        f.load()
        self.assertTrue(f._is_loaded())
        self.assertTrue("Ciência da computação" in f.broader("Hardware"))


if __name__ == "__main__":
    print('Unit testing initiated')
    unittest.main()
