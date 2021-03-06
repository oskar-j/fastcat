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


class FastcatTestsGerman(unittest.TestCase):

    def setUp(self):
        # Preparing data for unit test
        self.f = fastcat.FastCat(language="de")
        self.f.load(progress_bar=False)

    def test_narrower(self):
        self.assertTrue(self.f._is_loaded(language='de'),
                        msg="German-language Wikipedia successfully loaded?")
        self.assertTrue('Nikola Tesla' in self.f.narrower("Wissenschaftler als Thema"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='de'),
                        msg="German-language Wikipedia successfully loaded?")
        self.assertTrue('Nikola Tesla' in self.f.broader("Nikola Tesla als Namensgeber"))


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


class FastcatTestsRussian(unittest.TestCase):

    def setUp(self):
        # Preparing data for unit test
        self.f = fastcat.FastCat(language="ru")
        self.f.load(progress_bar=False)

    def test_narrower(self):
        self.assertTrue(self.f._is_loaded(language='ru'),
                        msg="Russian-language Wikipedia successfully loaded?")
        self.assertTrue('Борщ' in self.f.narrower("Русские супы"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='ru'),
                        msg="Russian-language Wikipedia successfully loaded?")
        self.assertTrue('Русская кухня' in self.f.broader("Русские супы"))


class FastcatTestsUkrainian(unittest.TestCase):

    def setUp(self):
        # Preparing data for unit test
        self.f = fastcat.FastCat(language="ua")
        self.f.load(progress_bar=False)

    def test_narrower(self):
        self.assertTrue(self.f._is_loaded(language='ua'),
                        msg="Ukrainian-language Wikipedia successfully loaded?")
        self.assertTrue('Київське князівство' in self.f.narrower("Київська Русь"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='ua'),
                        msg="Ukrainian-language Wikipedia successfully loaded?")
        self.assertTrue('Київщина' in self.f.broader("Київська Русь"))


class FastcatTestsEstonian(unittest.TestCase):

    def setUp(self):
        # Preparing data for unit test
        self.f = fastcat.FastCat(language="et")
        self.f.load(progress_bar=False)

    def test_narrower(self):
        self.assertTrue(self.f._is_loaded(language='et'),
                        msg="Estonian-language Wikipedia successfully loaded?")
        self.assertTrue('Tallinna geograafia' in self.f.narrower("Tallinn"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='et'),
                        msg="Estonian-language Wikipedia successfully loaded?")
        self.assertTrue('Eesti linnad' in self.f.broader("Tallinn"))


class FastcatTestsCzech(unittest.TestCase):

    def setUp(self):
        # Preparing data for unit test
        self.f = fastcat.FastCat(language="cs")
        self.f.load(progress_bar=False)

    def test_narrower(self):
        self.assertTrue(self.f._is_loaded(language='cs'),
                        msg="Czech-language Wikipedia successfully loaded?")
        self.assertTrue('Pivovary' in self.f.narrower("Průmyslové stavby"))

    def test_broader(self):
        self.assertTrue(self.f._is_loaded(language='cs'),
                        msg="Czech-language Wikipedia successfully loaded?")
        self.assertTrue('Pivo' in self.f.broader("Pivovary"))


if __name__ == "__main__":
    print('Unit testing initiated. Testing languages: cs, en, et, de, pt, ja, pl, ru, ua.')
    unittest.main()
