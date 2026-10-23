"""Offline checks on how FastCat resolves the language it is given (#22).

An unrecognised language must fail with a ValueError before it reaches the
slot store or Redis, and every accepted spelling of a language must end up in
the same Redis db.
"""

import bz2
import os

import pytest

import fastcat.interface as interface
from fastcat.interface import FastCat

BROADER = 'http://www.w3.org/2004/02/skos/core#broader'
UK_CATEGORY = 'http://uk.dbpedia.org/resource/Категорія:'


class UntouchableRedis:
    """A client that fails the test if fastcat uses it at all."""

    def __getattr__(self, name):
        raise AssertionError('Redis was used: {}'.format(name))


class RecordingRedis:
    """Just enough of a client for load() to fill."""

    def __init__(self):
        self.sets, self.flags = {}, {}

    def get(self, key):
        return self.flags.get(key)

    def set(self, key, value):
        self.flags[key] = value

    def pipeline(self, transaction=True):
        return self

    def sadd(self, key, value):
        self.sets.setdefault(key, set()).add(value)

    def execute(self):
        return []


def _db_index(client):
    return client.db.connection_pool.connection_kwargs['db']


@pytest.mark.parametrize('spelling', ['uk', 'UK', 'uk-UA', 'ukr', 'ua'])
def test_every_spelling_of_ukrainian_shares_one_db(isolated_store, spelling):
    reference = FastCat(language='ua')

    assert _db_index(FastCat(language=spelling)) == _db_index(reference)
    assert isolated_store.languages == {'en': 0, 'ua': 1}


@pytest.mark.parametrize('language', ['fr', 'kl', 'english', ''])
def test_an_unknown_language_is_rejected_before_the_store_is_touched(isolated_store, language):
    with pytest.raises(ValueError, match='Unsupported language'):
        FastCat(language=language)

    assert isolated_store.languages == {'en': 0}
    assert not os.path.exists(isolated_store.settings_filename)


def test_switching_to_an_unknown_language_is_rejected(isolated_store):
    f = FastCat()

    with pytest.raises(ValueError, match='Unsupported language'):
        f.switch_language('fr')

    assert _db_index(f) == 0
    assert isolated_store.languages == {'en': 0}


def test_switching_accepts_an_alias(isolated_store):
    isolated_store.save_settings('ua')  # already allocated, so no load() is triggered
    f = FastCat()

    f.switch_language('uk')

    assert _db_index(f) == isolated_store.get_slot('ua')


def test_loading_an_unknown_language_is_rejected_before_redis_is_used(isolated_store):
    with pytest.raises(ValueError, match='Unsupported language'):
        FastCat(db=UntouchableRedis()).load(language='fr', progress_bar=False)


def test_loading_by_alias_uses_the_language_id(isolated_store, tmp_path, monkeypatch):
    path = tmp_path / 'uk.nt.bz2'
    with bz2.open(path, 'wt', encoding='utf-8') as dump:
        dump.write('<{c}Київська_Русь> <{b}> <{c}Київщина> .\n'.format(
            c=UK_CATEGORY, b=BROADER))

    asked_for = []

    def skos_file_for(language, engine):
        asked_for.append(language)
        return str(path)

    monkeypatch.setattr(interface, 'skos_file_for', skos_file_for)
    client = RecordingRedis()

    FastCat(db=client).load(language='uk', progress_bar=False)

    # Before #22 'uk' got as far as the category-prefix lookup and raised
    # NotImplementedError there
    assert asked_for == ['ua']
    assert client.sets['b:Київська Русь'] == {'Київщина'}
    assert client.sets['n:Київщина'] == {'Київська Русь'}
