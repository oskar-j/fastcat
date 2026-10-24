"""Offline checks on FastCat with a Redis client of the caller's own (#23).

A language given to the constructor must hold whatever db the client points
at: load() fills that db with it and get_current_language() reports it. Left
out, the slot store still decides, as before. And since any db can now be
given any language, load() refuses to put one language on top of another.
"""

import bz2
from types import SimpleNamespace

import pytest

import fastcat.interface as interface
from fastcat.interface import FastCat

BROADER = 'http://www.w3.org/2004/02/skos/core#broader'
ET_CATEGORY = 'http://et.dbpedia.org/resource/Kategooria:'


class FakeRedis:
    """Just enough of a client on a given db for FastCat to use."""

    def __init__(self, db=15, flags=None):
        self.connection_pool = SimpleNamespace(connection_kwargs={'db': db})
        self.flags = dict(flags or {})
        self.sets = {}
        self.writes = []

    def get(self, key):
        return self.flags.get(key)

    def set(self, key, value):
        self.flags[key] = value
        self.writes.append(key)

    def pipeline(self, transaction=True):
        return self

    def sadd(self, key, value):
        self.sets.setdefault(key, set()).add(value)
        self.writes.append(key)

    def execute(self):
        return []


@pytest.fixture
def estonian_dump(tmp_path, monkeypatch):
    """Serve a one-relation Estonian dump; returns the languages asked for."""
    path = tmp_path / 'et.nt.bz2'
    with bz2.open(path, 'wt', encoding='utf-8') as dump:
        dump.write('<{c}Tallinn> <{b}> <{c}Eesti_linnad> .\n'.format(c=ET_CATEGORY, b=BROADER))

    asked_for = []

    def skos_file_for(language, engine):
        asked_for.append(language)
        return str(path)

    monkeypatch.setattr(interface, 'skos_file_for', skos_file_for)
    return asked_for


def _loaded(language, engine=b'wiki-archive'):
    flags = {'loaded-skos': b'1', 'loaded-engine': engine}
    if language is not None:
        flags['loaded-language'] = language
    return flags


def test_a_named_language_is_loaded_into_your_own_client(isolated_store, estonian_dump):
    client = FakeRedis(db=15)

    FastCat(db=client, language='et').load(progress_bar=False)

    assert estonian_dump == ['et']
    assert client.sets['b:Tallinn'] == {'Eesti linnad'}
    assert client.flags['loaded-language'] == 'et'
    # the slot store is the caller's business only when fastcat picks the db
    assert isolated_store.languages == {'en': 0}


def test_your_own_client_reports_the_named_language(isolated_store):
    f = FastCat(db=FakeRedis(db=15), language='est')

    assert f.get_current_language().name == 'Estonian'


def test_a_named_language_wins_over_the_slot_store(isolated_store, estonian_dump):
    isolated_store.save_settings('de')  # db 1 is German as far as the store knows
    f = FastCat(db=FakeRedis(db=1), language='et')

    assert f.get_current_language().name == 'Estonian'

    f.load(progress_bar=False)

    assert estonian_dump == ['et']


def test_without_a_language_the_slot_store_still_decides(isolated_store):
    isolated_store.save_settings('de')

    assert FastCat(db=FakeRedis(db=1)).get_current_language().name == 'German'


def test_without_a_language_an_unassigned_db_is_a_clear_error(isolated_store):
    client = FakeRedis(db=15)
    f = FastCat(db=client)

    assert f.get_current_language() is None

    # It used to be AttributeError: 'NoneType' object has no attribute 'alpha_2'
    with pytest.raises(ValueError, match="language='et'"):
        f.load(progress_bar=False)

    assert client.writes == []


def test_the_default_object_is_english(isolated_store):
    f = FastCat()

    assert f.language == 'en'
    assert f.get_current_language().name == 'English'


def test_switching_language_updates_it(isolated_store):
    isolated_store.save_settings('de')  # already allocated, so no load() is triggered
    f = FastCat()

    f.switch_language('ger')

    assert f.language == 'de'
    assert f.get_current_language().name == 'German'


def test_another_language_is_not_loaded_on_top(isolated_store, estonian_dump):
    client = FakeRedis(db=1, flags=_loaded(b'de'))

    with pytest.raises(RuntimeError) as excinfo:
        FastCat(db=client, language='et').load(progress_bar=False)

    assert "'de'" in str(excinfo.value) and "'et'" in str(excinfo.value)
    assert estonian_dump == []
    assert client.writes == []


def test_another_language_is_reported_before_another_engine(isolated_store, estonian_dump):
    client = FakeRedis(db=1, flags=_loaded(b'de', engine=b'databus'))

    with pytest.raises(RuntimeError, match="already holds 'de'"):
        FastCat(db=client, language='et').load(progress_bar=False)


def test_the_same_language_is_still_skipped(isolated_store, estonian_dump, capsys):
    client = FakeRedis(db=1, flags=_loaded(b'et'))

    FastCat(db=client, language='et').load(progress_bar=False)

    assert 'Loading aborted' in capsys.readouterr().out
    assert client.writes == []


def test_data_from_before_the_language_was_recorded_is_left_alone(isolated_store, estonian_dump,
                                                                   capsys):
    # Nothing to compare against, so behave as before: treat it as loaded
    client = FakeRedis(db=1, flags=_loaded(None))

    FastCat(db=client, language='et').load(progress_bar=False)

    assert 'Loading aborted' in capsys.readouterr().out
    assert client.writes == []
