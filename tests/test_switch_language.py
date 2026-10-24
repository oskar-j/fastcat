"""Offline checks on switch_language() keeping the connection (#28).

Switching moves the object to another db on the same Redis server, so
whatever the client was set up with must carry over, a client passed in as
``db`` included. No server is needed: redis-py only connects on the first
command.
"""

import pytest
import redis

from fastcat.interface import FastCat

SERVER = {'host': 'redis.example.internal', 'port': 6390, 'password': 's3cret'}


def _settings(f):
    kwargs = f.db.connection_pool.connection_kwargs
    return {key: kwargs.get(key) for key in ('host', 'port', 'password', 'db')}


@pytest.fixture
def german_slot(isolated_store):
    """German already has a db, so switching to it triggers no load()."""
    isolated_store.save_settings('de')
    return isolated_store.get_slot('de')


def test_your_own_clients_server_and_password_are_kept(german_slot):
    f = FastCat(db=redis.Redis(db=7, **SERVER))

    f.switch_language('de')

    # It used to be {'host': 'localhost', 'port': 6379, 'password': None, ...}
    assert _settings(f) == dict(SERVER, db=german_slot)
    assert f.language == 'de'


def test_ssl_is_kept(german_slot):
    f = FastCat(db=redis.Redis(host='redis.example.internal', ssl=True))

    f.switch_language('de')

    assert f.db.connection_pool.connection_class is redis.SSLConnection


def test_a_unix_socket_is_kept(german_slot):
    f = FastCat(db=redis.Redis(unix_socket_path='/tmp/redis.sock'))

    f.switch_language('de')

    pool = f.db.connection_pool
    assert pool.connection_class is redis.UnixDomainSocketConnection
    assert pool.connection_kwargs['path'] == '/tmp/redis.sock'
    assert pool.connection_kwargs['db'] == german_slot


def test_username_and_timeouts_are_kept(german_slot):
    f = FastCat(db=redis.Redis(host='redis.example.internal', username='fastcat',
                               socket_timeout=3.5))

    f.switch_language('de')

    kwargs = f.db.connection_pool.connection_kwargs
    assert kwargs['username'] == 'fastcat'
    assert kwargs['socket_timeout'] == 3.5


def test_constructor_keyword_arguments_are_still_kept(german_slot):
    # This always worked, and must keep working
    f = FastCat(**SERVER)

    f.switch_language('de')

    assert _settings(f) == dict(SERVER, db=german_slot)


def test_switching_back_and_forth_stays_on_the_server(german_slot):
    f = FastCat(db=redis.Redis(db=7, **SERVER))

    f.switch_language('de')
    f.switch_language('en')

    assert _settings(f) == dict(SERVER, db=0)
    assert f.language == 'en'


def test_a_new_language_is_loaded_into_the_same_server(isolated_store, monkeypatch):
    loaded = []

    def load(self, language=None, **kwargs):
        loaded.append((language, _settings(self)))

    monkeypatch.setattr(FastCat, 'load', load)
    f = FastCat(db=redis.Redis(db=7, **SERVER))

    f.switch_language('et')

    # It used to download the dump and load it into whatever ran on localhost
    assert loaded == [('et', dict(SERVER, db=isolated_store.get_slot('et')))]
