"""Offline checks on the load path, driven by a stand-in Redis client.

These cover what used to need a live Redis: that triples land as b:/n: pairs,
that writes are actually batched into pipelines, and that the "loaded-skos"
flag is only set once every triple is in.
"""

import bz2

import pytest

import fastcat.interface as interface
from fastcat.interface import DEFAULT_BATCH_SIZE, FastCat

BROADER = 'http://www.w3.org/2004/02/skos/core#broader'
PREF_LABEL = 'http://www.w3.org/2004/02/skos/core#prefLabel'
RESOURCE = 'http://dbpedia.org/resource/Category:'


class FakePipeline:
    """Records buffered commands and applies them to the owning client."""

    def __init__(self, owner):
        self.owner = owner
        self.buffer = []

    def sadd(self, key, value):
        self.buffer.append((key, value))

    def execute(self):
        self.owner.flushes.append(len(self.buffer))
        self.owner.events.append(('execute', len(self.buffer)))
        for key, value in self.buffer:
            self.owner.sets.setdefault(key, set()).add(value)
        self.buffer = []
        return []


class FakeRedis:

    def __init__(self):
        self.sets = {}
        self.flags = {}
        self.flushes = []
        self.events = []
        self.pipeline_transaction = None

    def get(self, key):
        return self.flags.get(key)

    def set(self, key, value):
        self.flags[key] = value
        self.events.append(('set', key))

    def pipeline(self, transaction=True):
        self.pipeline_transaction = transaction
        return FakePipeline(self)


def _dump(tmp_path, lines, name='dump.nt.bz2'):
    path = tmp_path / name
    with bz2.open(path, 'wt', encoding='utf-8') as handle:
        handle.writelines(lines)
    return str(path)


@pytest.fixture
def dump_path(tmp_path, monkeypatch):
    """A three-relation English dump, with a header and one irrelevant triple."""
    lines = [
        '# started 2017-03-14T08:38:43Z\n',
        '<{r}Futurama> <{p}> "Futurama"@en .\n'.format(r=RESOURCE, p=PREF_LABEL),
        '<{r}Computer_programming> <{b}> <{r}Software_engineering> .\n'.format(
            r=RESOURCE, b=BROADER),
        '<{r}Functional_programming> <{b}> <{r}Computer_programming> .\n'.format(
            r=RESOURCE, b=BROADER),
        '<{r}Debugging> <{b}> <{r}Computer_programming> .\n'.format(
            r=RESOURCE, b=BROADER),
    ]
    path = _dump(tmp_path, lines)
    monkeypatch.setattr(interface, 'skos_file_for', lambda language, engine: path)
    return path


@pytest.fixture
def client():
    return FakeRedis()


def test_triples_become_broader_and_narrower_pairs(client, dump_path):
    FastCat(db=client).load(language='en', progress_bar=False)

    assert client.sets['b:Computer programming'] == {'Software engineering'}
    assert client.sets['b:Functional programming'] == {'Computer programming'}
    assert client.sets['n:Computer programming'] == {'Functional programming', 'Debugging'}
    assert client.sets['n:Software engineering'] == {'Computer programming'}


def test_header_and_non_broader_triples_are_ignored(client, dump_path):
    FastCat(db=client).load(language='en', progress_bar=False)

    assert not any('Futurama' in key for key in client.sets)


def test_writes_are_pipelined_without_a_transaction(client, dump_path):
    FastCat(db=client).load(language='en', progress_bar=False)

    assert client.pipeline_transaction is False


def test_a_large_batch_flushes_once(client, dump_path):
    FastCat(db=client).load(language='en', progress_bar=False)

    # 3 relations -> 6 commands, well under the default batch
    assert client.flushes == [6]


def test_a_small_batch_flushes_repeatedly(client, dump_path):
    FastCat(db=client).load(language='en', progress_bar=False, batch_size=2)

    assert client.flushes == [2, 2, 2]


def test_loaded_flags_are_set_only_after_every_write(client, dump_path):
    FastCat(db=client).load(language='en', progress_bar=False, batch_size=2)

    assert client.events[-2:] == [('set', 'loaded-skos'), ('set', 'loaded-engine')]
    assert client.flags['loaded-skos'] == '1'
    assert all(event[0] == 'execute' for event in client.events[:-2])


def test_the_loading_engine_is_recorded(client, dump_path):
    FastCat(db=client).load(language='en', progress_bar=False)

    assert client.flags['loaded-engine'] == 'wiki-archive'


def test_batching_does_not_change_the_result(dump_path):
    batched, unbatched = FakeRedis(), FakeRedis()

    FastCat(db=batched).load(language='en', progress_bar=False, batch_size=DEFAULT_BATCH_SIZE)
    FastCat(db=unbatched).load(language='en', progress_bar=False, batch_size=1)

    assert batched.sets == unbatched.sets
    assert len(unbatched.flushes) > len(batched.flushes)


def test_progress_bar_does_not_break_loading(client, dump_path, capsys):
    FastCat(db=client).load(language='en', progress_bar=True)

    assert client.sets['b:Computer programming'] == {'Software engineering'}
    assert '100.0%' in capsys.readouterr().out


def test_an_already_loaded_language_is_not_reloaded(client, dump_path):
    client.flags['loaded-skos'] = '1'

    FastCat(db=client).load(language='en', progress_bar=False)

    assert client.sets == {}


@pytest.mark.parametrize('batch_size', [0, -1])
def test_a_meaningless_batch_size_is_rejected(client, dump_path, batch_size):
    with pytest.raises(ValueError):
        FastCat(db=client).load(language='en', progress_bar=False, batch_size=batch_size)
