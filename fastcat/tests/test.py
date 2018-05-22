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
        self.assertTrue('Functional languages' in self.f.narrower("Functional programming"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='en'),
                        msg="English-language Wikipedia successfully loaded?")
        self.assertTrue('Software engineering' in self.f.broader("Computer programming"))


class FastcatTestsPortuguese(unittest.TestCase):

    def setUp(self):
        # Preparing data for unit test
        self.f = fastcat.FastCat(language="pt")
        self.f.load(progress_bar=False)

    def test_narrower(self):
        self.assertTrue(self.f._is_loaded(language='pt'),
                        msg="Portuguese-language Wikipedia successfully loaded?")
        self.assertTrue('Computadores' in self.f.narrower("Hardware"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='pt'),
                        msg="Portuguese-language Wikipedia successfully loaded?")
        self.assertTrue('Hardware' in self.f.broader("Placas de som"))


class FastcatTestsJapanese(unittest.TestCase):

    def setUp(self):
        # Preparing data for unit test
        self.f = fastcat.FastCat(language="ja")
        self.f.load(progress_bar=False)

    def test_narrower(self):
        self.assertTrue(self.f._is_loaded(language='ja'),
                        msg="Japanese-language Wikipedia successfully loaded?")
        self.assertTrue('都道府県庁' in self.f.narrower("日本の都道府県"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='ja'),
                        msg="Japanese-language Wikipedia successfully loaded?")
        self.assertTrue('日本の行政区画' in self.f.broader("日本の都道府県"))


class FastcatTestsPolish(unittest.TestCase):

    def setUp(self):
        # Preparing data for unit test
        self.f = fastcat.FastCat(language="pl")
        self.f.load(progress_bar=False)

    def test_narrower(self):
        self.assertTrue(self.f._is_loaded(language='pl'),
                        msg="Polish-language Wikipedia successfully loaded?")
        self.assertTrue('Husaria' in self.f.narrower("Jeździectwo"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='pl'),
                        msg="Polish-language Wikipedia successfully loaded?")
        self.assertTrue('Jeździectwo' in self.f.broader("Husaria"))


if __name__ == "__main__":
    print('Unit testing initiated. Testing languages: en, pt, ja, pl.')
    unittest.main()
