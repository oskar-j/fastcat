"""Offline checks on downloading and caching a dump (#27).

A small HTTP server on localhost stands in for DBpedia. It can serve a dump
whole, drop the connection halfway, stall, or answer 404. Whatever happens,
the cache must end up holding either a complete dump or nothing, because
load() uses any cached file as it is.
"""

import bz2
import hashlib
import http.server
import os
import threading
import time
from types import SimpleNamespace

import pytest

import fastcat.interface as interface
from fastcat.engines import DownloadSource
from fastcat.interface import DamagedDumpError, FastCat

BROADER = 'http://www.w3.org/2004/02/skos/core#broader'
ET_CATEGORY = 'http://et.dbpedia.org/resource/Kategooria:'

DUMP = bz2.compress(''.join(
    '<{c}Linn_{i}> <{b}> <{c}Eesti_linnad> .\n'.format(c=ET_CATEGORY, b=BROADER, i=i)
    for i in range(2000)).encode('utf-8'))

CACHED_NAME = 'skos-wiki-archive-et.nt.bz2'


class FakeRedis:
    """Just enough of a client on db 15 for FastCat to load into."""

    def __init__(self):
        self.connection_pool = SimpleNamespace(connection_kwargs={'db': 15})
        self.flags = {}
        self.sets = {}

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


class DumpServer:
    """Serves DUMP in one of several ways; see ``mode``."""

    def __init__(self):
        self.mode = 'whole'
        self.stall = 1.0
        self.sha256 = None
        self.requests = 0
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):

            def do_GET(self):
                server.requests += 1

                if server.mode == 'missing':
                    self.send_error(404)
                    return

                self.send_response(200)
                self.send_header('Content-Length', str(len(DUMP)))
                self.end_headers()

                if server.mode == 'whole':
                    self.wfile.write(DUMP)
                elif server.mode == 'cut':
                    # Half the promised bytes, then the connection closes
                    self.wfile.write(DUMP[:len(DUMP) // 2])
                elif server.mode == 'stall':
                    self.wfile.write(DUMP[:100])
                    self.wfile.flush()
                    time.sleep(server.stall)

            def log_message(self, *args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = 'http://127.0.0.1:{}/skos.ttl.bz2'.format(self.httpd.server_port)
        # A short poll interval keeps shutdown(), and so each test, quick
        threading.Thread(target=self.httpd.serve_forever, kwargs={'poll_interval': 0.01},
                         daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server(monkeypatch, isolated_store):
    """A dump server. fastcat's data directory is tmp_path (see conftest)."""
    dumps = DumpServer()

    monkeypatch.setattr(interface, 'skos_source',
                        lambda mapping, engine: DownloadSource(url=dumps.url,
                                                               sha256=dumps.sha256))
    yield dumps
    dumps.close()


def _load(client=None):
    client = client or FakeRedis()
    FastCat(db=client, language='et').load(progress_bar=False)
    return client


def test_a_whole_download_is_cached_and_loaded(server, tmp_path):
    client = _load()

    assert client.sets['b:Linn 0'] == {'Eesti linnad'}
    assert client.flags['loaded-skos'] == '1'
    # and no temporary file is left next to it
    assert os.listdir(tmp_path) == [CACHED_NAME]


def test_a_download_cut_short_leaves_nothing_cached(server, tmp_path):
    server.mode = 'cut'
    client = FakeRedis()

    with pytest.raises(RuntimeError, match='Nothing was cached'):
        _load(client)

    assert os.listdir(tmp_path) == []
    assert client.sets == {} and 'loaded-skos' not in client.flags

    # so the next load() downloads it again, rather than failing on it
    server.mode = 'whole'
    client = _load()

    assert server.requests == 2
    assert client.sets['b:Linn 0'] == {'Eesti linnad'}


def test_a_stalled_download_times_out_and_leaves_nothing_cached(server, tmp_path, monkeypatch):
    monkeypatch.setattr(interface, 'DOWNLOAD_TIMEOUT', 0.2)
    server.mode = 'stall'

    with pytest.raises(RuntimeError, match='interrupted .*Nothing was cached'):
        _load()

    assert os.listdir(tmp_path) == []


def test_ctrl_c_during_a_download_leaves_nothing_cached(server, tmp_path, monkeypatch):
    class Response:
        headers = {'Content-Length': str(len(DUMP))}
        sent = False

        def info(self):  # what urlretrieve() used to ask for
            return self.headers

        def read(self, size=-1):
            if self.sent:
                raise KeyboardInterrupt
            self.sent = True
            return DUMP[:100]

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(interface.request, 'urlopen', lambda *args, **kwargs: Response())

    with pytest.raises(KeyboardInterrupt):
        _load()

    assert os.listdir(tmp_path) == []


def test_a_checksum_mismatch_leaves_nothing_cached(server, tmp_path):
    server.sha256 = '0' * 64

    with pytest.raises(RuntimeError, match='Checksum mismatch'):
        _load()

    assert os.listdir(tmp_path) == []


def test_a_matching_checksum_is_cached(server, tmp_path):
    server.sha256 = hashlib.sha256(DUMP).hexdigest()

    _load()

    assert os.listdir(tmp_path) == [CACHED_NAME]


def test_a_missing_dump_is_reported_and_nothing_cached(server, tmp_path):
    server.mode = 'missing'

    with pytest.raises(RuntimeError, match='may no longer serve this file'):
        _load()

    assert os.listdir(tmp_path) == []


@pytest.mark.skipif(os.name == 'nt', reason='POSIX permission bits')
def test_the_cached_dump_gets_the_usual_permissions(server, tmp_path):
    umask = os.umask(0)
    os.umask(umask)

    _load()

    assert os.stat(tmp_path / CACHED_NAME).st_mode & 0o777 == 0o666 & ~umask


@pytest.mark.parametrize('damage', ['truncated', 'garbage'])
def test_a_damaged_cached_dump_is_deleted_then_downloaded_again(server, tmp_path, damage):
    # What 0.3.3 and earlier could leave behind after an interrupted download
    cached = tmp_path / CACHED_NAME
    cached.write_bytes(DUMP[:len(DUMP) // 2] if damage == 'truncated' else b'not bzip2 at all')
    client = FakeRedis()

    with pytest.raises(DamagedDumpError, match='incomplete or damaged.*load\\(\\) again'):
        _load(client)

    assert not cached.exists()
    assert server.requests == 0
    assert 'loaded-skos' not in client.flags

    client = _load(client)

    assert server.requests == 1
    assert client.sets['b:Linn 0'] == {'Eesti linnad'}
    assert client.flags['loaded-skos'] == '1'


def test_a_damaged_dump_is_still_a_runtime_error():
    # Callers catching RuntimeError around load() keep working
    assert issubclass(DamagedDumpError, RuntimeError)


# --- the data directory (#33) ---------------------------------------------------

def test_the_data_directory_is_created_by_the_first_download(server, tmp_path, monkeypatch):
    monkeypatch.setenv('FASTCAT_DATA_DIR', str(tmp_path / 'a' / 'b'))

    _load()

    assert os.listdir(tmp_path / 'a' / 'b') == [CACHED_NAME]


def test_a_data_directory_that_cannot_be_created_is_reported(server, tmp_path, monkeypatch):
    (tmp_path / 'a-file').write_text('')
    monkeypatch.setenv('FASTCAT_DATA_DIR', str(tmp_path / 'a-file' / 'fastcat'))

    with pytest.raises(RuntimeError, match='cannot write to its data directory .*FASTCAT_DATA_DIR'):
        _load()

    assert server.requests == 0


@pytest.mark.skipif(os.name == 'nt' or (hasattr(os, 'geteuid') and os.geteuid() == 0),
                    reason='POSIX permission bits, which root ignores')
def test_a_read_only_data_directory_is_reported(server, tmp_path, monkeypatch):
    directory = tmp_path / 'read-only'
    directory.mkdir()
    directory.chmod(0o555)
    monkeypatch.setenv('FASTCAT_DATA_DIR', str(directory))

    try:
        with pytest.raises(RuntimeError, match='cannot write to its data directory .*FASTCAT_DATA_DIR'):
            _load()
    finally:
        directory.chmod(0o755)

    assert server.requests == 0
    assert os.listdir(directory) == []
