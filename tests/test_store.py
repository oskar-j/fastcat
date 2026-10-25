"""Offline checks on the language -> Redis db-slot bookkeeping."""

import os

import pytest

import fastcat.lang as languages
import fastcat.store as store
from fastcat.interface import FastCat
from fastcat.utils import supported_language_ids


def test_english_owns_slot_zero_on_first_run(isolated_store):
    assert isolated_store.get_slot('en') == 0


def test_unknown_language_raises(isolated_store):
    with pytest.raises(ValueError):
        isolated_store.get_slot('pl')


def test_new_languages_take_consecutive_slots(isolated_store):
    assert isolated_store.save_settings('pl') == 1
    assert isolated_store.save_settings('de') == 2
    assert isolated_store.get_slot('pl') == 1
    assert isolated_store.get_slot('de') == 2


def test_slots_survive_a_reload(isolated_store):
    isolated_store.save_settings('pl')

    isolated_store.languages.clear()
    isolated_store.load_settings()

    assert isolated_store.get_slot('pl') == 1


def test_language_is_resolvable_from_its_slot(isolated_store):
    isolated_store.save_settings('pl')

    assert isolated_store.get_language(slot=1).alpha_2.lower() == 'pl'


def test_unassigned_slot_resolves_to_none(isolated_store):
    assert isolated_store.get_language(slot=15) is None


@pytest.mark.parametrize('key', [None, 'da', 'uk', 'pt-BR'])
def test_only_language_ids_are_given_a_slot(isolated_store, key):
    # Unrecognised codes used to reach here as None and were pickled for good,
    # holding a Redis db (#22). Aliases must be normalised before this point.
    with pytest.raises(ValueError):
        isolated_store.save_settings(key)

    assert isolated_store.languages == {'en': 0}
    assert not os.path.exists(isolated_store.settings_file())


# --- what each language is reported as (#30) ---------------------------------

NAMES = {'cs': 'Czech', 'de': 'German', 'en': 'English', 'es': 'Spanish', 'et': 'Estonian',
         'fi': 'Finnish', 'fr': 'French', 'hu': 'Hungarian', 'it': 'Italian', 'ja': 'Japanese',
         'nl': 'Dutch', 'pl': 'Polish', 'pt': 'Portuguese', 'ru': 'Russian', 'sv': 'Swedish',
         'ua': 'Ukrainian'}


def test_every_supported_language_has_an_expected_name():
    assert sorted(NAMES) == supported_language_ids()


@pytest.mark.parametrize('language', languages.available_languages.values(), ids=lambda l: l.id)
def test_every_language_is_reported_as_a_language(language):
    info = store.language_info(language.id)

    assert info.name == NAMES[language.id]
    # A language record carries the lower-case ISO 639-1 code; pycountry's
    # country records (Ukraine is 'UA') do not
    assert info.alpha_2 == language.wikipedia_mapping


def test_ukrainian_is_reported_as_the_language_not_the_country(isolated_store):
    current = FastCat(language='uk').get_current_language()

    # It used to be pycountry's record for Ukraine, the country: 'Ukraine', 'UA'
    assert current.name == 'Ukrainian'
    assert current.alpha_2 == 'uk'


def test_ukrainian_is_resolvable_from_its_slot(isolated_store):
    isolated_store.save_settings('ua')

    assert isolated_store.get_language(slot=1).name == 'Ukrainian'


def test_an_unknown_id_has_no_record():
    # The old country fallback raised IndexError here
    assert store.language_info('zz') is None


# --- Redis has 16 dbs (#35) ---------------------------------------------------

def test_every_supported_language_fits_in_redis(isolated_store):
    for language in supported_language_ids():
        if language != 'en':
            isolated_store.save_settings(language)

    assert sorted(isolated_store.languages.values()) == list(range(16))


def test_no_db_past_the_last_is_given_out(isolated_store):
    # A mapping from before 0.3.2 could hold slots for unsupported codes (#22)
    isolated_store.languages.update({None: 1, 'xx': 15})

    with pytest.raises(RuntimeError, match='Redis has 16 dbs.*none left for \'de\''):
        isolated_store.save_settings('de')

    assert 'de' not in isolated_store.languages
    assert not os.path.exists(isolated_store.settings_file())
