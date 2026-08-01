"""Offline checks on DBpedia resource-URL parsing.

Each DBpedia locale prefixes its category resources differently
(``Category:``, ``Kategorie:``, ``Категорія:`` ...), so ``_name`` carries one
regex per language. These tests are what catch a missing branch when a new
language is added.
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


def test_every_supported_language_has_a_name_branch(parser):
    # Guards against adding a language to lang.py while forgetting the regex.
    import fastcat.lang as languages

    covered = {case[0] for case in NAME_CASES}
    declared = {language.id for language in languages.available_languages.values()}
    assert declared == covered
