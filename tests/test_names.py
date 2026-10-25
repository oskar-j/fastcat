"""Offline checks on DBpedia resource-URL parsing.

Each DBpedia locale prefixes its category resources differently
(``Category:``, ``Kategorie:``, ``Категорія:`` ...), so each language in
``lang.py`` carries its ``category_prefix``. These tests check every one
against a URL as the dumps write it.
"""

import pytest

from fastcat.interface import FastCatBase

# (language id, resource URL, expected category name)
NAME_CASES = [
    ('en', 'http://dbpedia.org/resource/Category:Computer_programming',
     'Computer programming'),
    ('cs', 'http://cs.dbpedia.org/resource/Kategorie:Pivovary', 'Pivovary'),
    ('et', 'http://et.dbpedia.org/resource/Kategooria:Tallinn', 'Tallinn'),
    ('de', 'http://de.dbpedia.org/resource/Kategorie:Berlin', 'Berlin'),
    ('ja', 'http://ja.dbpedia.org/resource/Category:日本の都道府県', '日本の都道府県'),
    ('pl', 'http://pl.dbpedia.org/resource/Kategoria:Husaria', 'Husaria'),
    ('pt', 'http://pt.dbpedia.org/resource/Categoria:Hardware', 'Hardware'),
    ('ru', 'http://ru.dbpedia.org/resource/Категория:Борщ', 'Борщ'),
    ('ua', 'http://uk.dbpedia.org/resource/Категорія:Київська_Русь',
     'Київська Русь'),
    # Added in 0.4.0 (#35), each prefix as the 2016 and 2022 dumps write it
    ('fr', 'http://fr.dbpedia.org/resource/Catégorie:Produit_laitier', 'Produit laitier'),
    ('es', 'http://es.dbpedia.org/resource/Categoría:Capitales_de_Europa',
     'Capitales de Europa'),
    ('it', 'http://it.dbpedia.org/resource/Categoria:Cucina_italiana', 'Cucina italiana'),
    ('sv', 'http://sv.dbpedia.org/resource/Kategori:Europas_huvudstäder',
     'Europas huvudstäder'),
    ('nl', 'http://nl.dbpedia.org/resource/Categorie:Gemeente_in_Noord-Holland',
     'Gemeente in Noord-Holland'),
    ('fi', 'http://fi.dbpedia.org/resource/Luokka:Euroopan_pääkaupungit',
     'Euroopan pääkaupungit'),
    ('hu', 'http://hu.dbpedia.org/resource/Kategória:Természettudományok',
     'Természettudományok'),
]


@pytest.fixture
def parser():
    return FastCatBase()


@pytest.mark.parametrize('language,url,expected', NAME_CASES,
                         ids=[case[0] for case in NAME_CASES])
def test_category_name_is_extracted(parser, language, url, expected):
    assert parser._name(url, language) == expected


def test_underscores_become_spaces(parser):
    name = parser._name(
        'http://dbpedia.org/resource/Category:Software_design_patterns', 'en')
    assert name == 'Software design patterns'


def test_percent_encoding_is_decoded(parser):
    name = parser._name('http://dbpedia.org/resource/Category:Caf%C3%A9s', 'en')
    assert name == 'Cafés'


def test_unsupported_language_raises(parser):
    with pytest.raises(NotImplementedError):
        parser._name('http://kl.dbpedia.org/resource/Category:Nuuk', 'kl')


@pytest.mark.parametrize('url', [
    # Another language's prefix, an article rather than a category, and a
    # prefix with nothing after it
    'http://de.dbpedia.org/resource/Kategorie:Berlin',
    'http://fr.dbpedia.org/resource/Fromage',
    'http://fr.dbpedia.org/resource/Catégorie:',
], ids=['other-language', 'not-a-category', 'no-name'])
def test_a_url_that_is_not_one_of_the_languages_categories_has_no_name(parser, url):
    assert parser._name(url, 'fr') is None


def test_every_supported_language_has_a_name_case(parser):
    # Every language in lang.py must be checked against a real URL above.
    import fastcat.lang as languages

    covered = {case[0] for case in NAME_CASES}
    declared = {language.id for language in languages.available_languages.values()}
    assert declared == covered
