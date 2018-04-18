import unittest
import fastcat


class FastcatTests(unittest.TestCase):

    def setUp(self):
        # Preparing data for unit test
        self.f = fastcat.FastCat()
        self.f.load(progress_bar=False)

    def test_narrower(self):
        self.assertTrue(self.f._is_loaded(language='en'),
                        msg="English-language Wikipedia successfully loaded?")
        self.assertTrue("Functional languages" in self.f.narrower("Functional programming"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='en'),
                        msg="English-language Wikipedia successfully loaded?")
        self.assertTrue("Computing" in self.f.broader("Computer programming"))


class FastcatTestsPortuguese(unittest.TestCase):

    def setUp(self):
        # Preparing data for unit test
        self.f = fastcat.FastCat(language="pt")
        self.f.load(progress_bar=False)

    def test_narrower(self):
        self.assertTrue(self.f._is_loaded(language='pt'),
                        msg="Portuguese-language Wikipedia successfully loaded?")
        self.assertTrue("Linguagens de programação funcionais‎" in self.f.narrower("Programação_funcional"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='pt'),
                        msg="Portuguese-language Wikipedia successfully loaded?")
        self.assertTrue("Ciência da computação" in self.f.broader("Hardware"))


if __name__ == "__main__":
    print('Unit testing initiated')
    unittest.main()
