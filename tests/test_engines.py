"""Offline checks on download engines and the URLs they build."""

import pytest

import fastcat
import fastcat.engines as engines
import fastcat.lang as languages
from fastcat.engines import DATABUS, DEFAULT_ENGINE, WIKI_ARCHIVE, skos_url, validate_engine
from fastcat.interface import FastCat, skos_file_for

ALL_LANGUAGES = list(languages.available_languages.values())


def test_wiki_archive_is_the_default_engine():
    assert DEFAULT_ENGINE == WIKI_ARCHIVE


def test_databus_is_known_but_not_implemented():
    assert DATABUS in engines.available_engines
    assert DATABUS not in engines.implemented_engines


def test_wiki_archive_is_implemented():
    assert WIKI_ARCHIVE in engines.implemented_engines


def test_validating_the_databus_engine_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        validate_engine(DATABUS)


def test_validating_an_unknown_engine_raises_value_error():
    with pytest.raises(ValueError):
        validate_engine('sparql')


@pytest.mark.parametrize('language', ALL_LANGUAGES, ids=lambda lang: lang.id)
def test_url_points_at_the_archived_release(language):
    url = skos_url(language.wikipedia_mapping)

    assert url == (
        'https://downloads.dbpedia.org/2016-10/core-i18n/'
        '{mapping}/skos_categories_{mapping}.ttl.bz2'.format(
            mapping=language.wikipedia_mapping))


def test_url_uses_the_dbpedia_subdomain_not_the_language_id():
    # Ukrainian is 'ua' in fastcat but lives under uk.dbpedia.org
    ukrainian = languages.available_languages['Ukrainian']

    assert '/uk/skos_categories_uk.ttl.bz2' in skos_url(ukrainian.wikipedia_mapping)


def test_url_is_not_built_for_the_databus_engine():
    with pytest.raises(NotImplementedError):
        skos_url('en', engine=DATABUS)


def test_url_is_not_built_for_an_unknown_engine():
    with pytest.raises(ValueError):
        skos_url('en', engine='sparql')


def test_cache_file_name_keeps_engines_apart():
    assert skos_file_for('en', WIKI_ARCHIVE) != skos_file_for('en', 'databus')
    assert skos_file_for('en', WIKI_ARCHIVE).endswith('skos-wiki-archive-en.nt.bz2')


def test_client_defaults_to_the_wiki_archive_engine():
    # No redis connection is opened until a command is issued, so this stays
    # an offline test.
    assert FastCat().engine == WIKI_ARCHIVE


def test_client_rejects_the_databus_engine():
    with pytest.raises(NotImplementedError):
        FastCat(engine=DATABUS)


def test_client_rejects_an_unknown_engine():
    with pytest.raises(ValueError):
        FastCat(engine='sparql')


def test_engine_names_are_exported_from_the_package():
    assert fastcat.WIKI_ARCHIVE == WIKI_ARCHIVE
    assert fastcat.DATABUS == DATABUS
    assert fastcat.DEFAULT_ENGINE == WIKI_ARCHIVE


def test_supported_engines_lists_both():
    assert set(FastCat.get_supported_engines()) == {WIKI_ARCHIVE, DATABUS}
    assert set(FastCat.get_implemented_engines()) == {WIKI_ARCHIVE}
