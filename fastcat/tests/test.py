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
        self.assertTrue(b'Functional languages' in self.f.narrower("Functional programming"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='en'),
                        msg="English-language Wikipedia successfully loaded?")
        self.assertTrue(b'Software engineering' in self.f.broader("Computer programming"))


class FastcatTestsPortuguese(unittest.TestCase):

    def setUp(self):
        # Preparing data for unit test
        self.f = fastcat.FastCat(language="pt")
        self.f.load(progress_bar=False)

    def test_narrower(self):
        self.assertTrue(self.f._is_loaded(language='pt'),
                        msg="Portuguese-language Wikipedia successfully loaded?")
        self.assertTrue(b'Computadores' in self.f.narrower("Hardware"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='pt'),
                        msg="Portuguese-language Wikipedia successfully loaded?")
        self.assertTrue(b'Hardware' in self.f.broader("Placas de som"))


if __name__ == "__main__":
    print('Unit testing initiated')
    unittest.main()
