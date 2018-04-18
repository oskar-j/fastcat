import unittest
import fastcat


class FastcatTests(unittest.TestCase):

    def test_narrower(self):
        # Preparing data for unit test
        f = fastcat.FastCat()
        f.load(progress_bar=False)

        self.assertTrue(f._is_loaded(language='en'),
                        msg="English-language Wikipedia successfully loaded?")
        self.assertTrue("Functional languages" in f.narrower("Functional programming"))

    def test_broader(self):
        f = fastcat.FastCat()
        f.load(progress_bar=False)

        self.assertTrue(f._is_loaded(language='en'),
                        msg="English-language Wikipedia successfully loaded?")
        self.assertTrue("Computing" in f.broader("Computer programming"))


class FastcatTestsPortuguese(unittest.TestCase):

    def test_narrower(self):
        f = fastcat.FastCat(language="pt")
        f.load(progress_bar=False)

        self.assertTrue(f._is_loaded(language='pt'),
                        msg="Portuguese-language Wikipedia successfully loaded?")
        self.assertTrue("Linguagens de programação funcionais‎" in f.narrower("Programação_funcional"))

    def test_broader(self):
        f = fastcat.FastCat(language="pt")
        f.load(progress_bar=False)

        self.assertTrue(f._is_loaded(language='pt'),
                        msg="Portuguese-language Wikipedia successfully loaded?")
        self.assertTrue("Ciência da computação" in f.broader("Hardware"))


if __name__ == "__main__":
    print('Unit testing initiated')
    unittest.main()
