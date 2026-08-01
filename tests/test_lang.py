"""Offline checks on the language table and its normalisation helpers."""

import pytest

import fastcat.lang as languages
from fastcat.utils import get_wikipedia_mapping, normalize_language

ALL_LANGUAGES = list(languages.available_languages.values())


def test_language_ids_are_unique():
    ids = [language.id for language in ALL_LANGUAGES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize('language', ALL_LANGUAGES, ids=lambda lang: lang.id)
def test_every_language_is_fully_specified(language):
    assert language.id and language.alternate and language.wikipedia_mapping
    assert language.locales


@pytest.mark.parametrize('language', ALL_LANGUAGES, ids=lambda lang: lang.id)
def test_id_normalizes_to_itself(language):
    assert normalize_language(language.id) == language.id


@pytest.mark.parametrize('language', ALL_LANGUAGES, ids=lambda lang: lang.id)
def test_locales_normalize_to_the_id(language):
    for locale in language.locales:
        assert normalize_language(locale) == language.id


@pytest.mark.parametrize('language', ALL_LANGUAGES, ids=lambda lang: lang.id)
def test_iso_639_2_code_normalizes_to_the_id(language):
    assert normalize_language(language.alternate) == language.id


@pytest.mark.parametrize('raw,expected', [
    ('EN', 'en'),
    ('En', 'en'),
    ('pt_BR', 'pt'),
    ('PT-BR', 'pt'),
    ('ENG', 'en'),
])
def test_normalization_is_case_and_separator_insensitive(raw, expected):
    assert normalize_language(raw) == expected


def test_unknown_language_normalizes_to_none():
    assert normalize_language('kl') is None


@pytest.mark.parametrize('language', ALL_LANGUAGES, ids=lambda lang: lang.id)
def test_wikipedia_mapping_is_resolvable(language):
    assert get_wikipedia_mapping(language.id) == language.wikipedia_mapping


def test_ukrainian_id_differs_from_its_dbpedia_subdomain():
    # 'ua' is the key used throughout fastcat, but DBpedia serves Ukrainian
    # under uk.dbpedia.org -- a mismatch that is easy to "fix" by accident.
    ukrainian = languages.available_languages['Ukrainian']
    assert ukrainian.id == 'ua'
    assert ukrainian.wikipedia_mapping == 'uk'
