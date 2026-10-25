"""Offline checks on where fastcat keeps its files (#33).

Up to 0.3.5 the dumps and the language -> db mapping lived inside the
installed package, and ``import fastcat`` created the directories for them,
so a read-only install could not even be imported. They now go to the
user's cache directory (or ``FASTCAT_DATA_DIR``), created when the first
file is written, and ``FastCat()`` moves the files an earlier version left
in the package.

conftest points the data directory at tmp_path, and the package directory
at an empty tmp_path/legacy-package, for every test.
"""

import bz2
import errno
import os
import pickle
import shutil
import subprocess
import sys
import warnings
from types import SimpleNamespace

import pytest

import fastcat.interface as interface
import fastcat.paths as paths
from fastcat.interface import FastCat

PACKAGE = os.path.dirname(os.path.realpath(interface.__file__))

DUMP_NAMES = ['skos-wiki-archive-de.nt.bz2', 'skos-databus-et.nt.bz2']


def _db_index(f):
    return f.db.connection_pool.connection_kwargs.get('db', 0)


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


# --- where the directory is ---------------------------------------------------

HOME = os.path.join(os.sep, 'home', 'you')


@pytest.mark.parametrize('platform, environ, expected', [
    ('linux', {}, os.path.join(HOME, '.cache', 'fastcat')),
    ('linux', {'XDG_CACHE_HOME': os.path.join(os.sep, 'xdg')}, os.path.join(os.sep, 'xdg', 'fastcat')),
    ('linux', {'XDG_CACHE_HOME': 'relative'}, os.path.join(HOME, '.cache', 'fastcat')),
    ('freebsd14', {}, os.path.join(HOME, '.cache', 'fastcat')),
    ('darwin', {'XDG_CACHE_HOME': os.path.join(os.sep, 'xdg')},
     os.path.join(HOME, 'Library', 'Caches', 'fastcat')),
    ('win32', {'LOCALAPPDATA': os.path.join('C:', 'Local')},
     os.path.join('C:', 'Local', 'fastcat', 'Cache')),
    ('win32', {}, os.path.join(HOME, 'AppData', 'Local', 'fastcat', 'Cache')),
], ids=['linux', 'xdg', 'relative-xdg', 'other-unix', 'macos', 'windows', 'windows-no-env'])
def test_the_default_is_the_users_cache_directory(platform, environ, expected):
    assert paths.default_data_dir(platform, environ, home=HOME) == expected


def test_the_default_applies_without_the_variable(monkeypatch):
    monkeypatch.delenv(paths.DATA_DIR_VARIABLE)

    assert paths.data_dir() == paths.default_data_dir()


def test_an_empty_variable_counts_as_unset(monkeypatch):
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, '')

    assert paths.data_dir() == paths.default_data_dir()


def test_the_variable_overrides_it_and_is_read_on_every_call(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path / 'first'))
    first = FastCat.get_data_dir()
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path / 'second'))

    assert first == str(tmp_path / 'first')
    assert FastCat.get_data_dir() == str(tmp_path / 'second')


def test_the_variable_may_start_with_a_tilde_or_be_relative(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, os.path.join('~', 'fastcat'))

    assert paths.data_dir() == str(tmp_path / 'fastcat')

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, 'relative')

    assert paths.data_dir() == str(tmp_path / 'relative')


def test_dumps_are_cached_there():
    assert interface.skos_file_for('de', 'databus') == os.path.join(
        FastCat.get_data_dir(), 'skos-databus-de.nt.bz2')


# --- nothing is written until it has to be -------------------------------------

def _listing(root):
    return sorted(os.path.relpath(os.path.join(directory, name), root)
                  for directory, dirs, files in os.walk(root) for name in dirs + files)


def test_importing_fastcat_from_a_read_only_install_works_and_writes_nothing(tmp_path):
    # The import itself used to create data/ and settings/ in the package,
    # and failed with a PermissionError where it couldn't
    site = tmp_path / 'site'
    package = site / 'fastcat'
    shutil.copytree(PACKAGE, package,
                    ignore=shutil.ignore_patterns('data', 'settings', '__pycache__'))
    before = _listing(site)
    home = tmp_path / 'home'
    home.mkdir()

    environ = {key: value for key, value in os.environ.items()
               if key not in (paths.DATA_DIR_VARIABLE, 'XDG_CACHE_HOME', 'LOCALAPPDATA')}
    # The copy goes first, ahead of wherever the dependencies are found
    environ.update(PYTHONPATH=os.pathsep.join(filter(None, [str(site), environ.get('PYTHONPATH')])),
                   PYTHONDONTWRITEBYTECODE='1', HOME=str(home), USERPROFILE=str(home))
    script = ('import fastcat\n'
              'assert fastcat.__file__.startswith({!r}), fastcat.__file__\n'
              'fastcat.FastCat()\n'
              'print(fastcat.FastCat.get_data_dir())\n').format(str(package))

    for path in [package] + [package / name for name in os.listdir(package)]:
        os.chmod(path, 0o555)
    try:
        result = subprocess.run([sys.executable, '-c', script], cwd=str(tmp_path),
                                env=environ, capture_output=True, text=True)
    finally:
        for path in [package] + [package / name for name in os.listdir(package)]:
            os.chmod(path, 0o755)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == paths.default_data_dir(environ={}, home=str(home))
    assert _listing(site) == before
    assert _listing(home) == []


def test_english_needs_nothing_written(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path / 'later'))

    FastCat()
    FastCat(language='en')

    assert not (tmp_path / 'later').exists()


def test_the_directory_is_created_when_the_mapping_is_first_saved(isolated_store, tmp_path,
                                                                  monkeypatch):
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path / 'a' / 'b'))

    f = FastCat(language='de')

    assert _db_index(f) == 1
    assert sorted(os.listdir(tmp_path / 'a' / 'b')) == ['redis_ids.pickle']
    assert pickle.loads((tmp_path / 'a' / 'b' / 'redis_ids.pickle').read_bytes()) == {
        'en': 0, 'de': 1}


@pytest.fixture
def blocked(tmp_path, monkeypatch):
    """A data directory that cannot be created, whoever runs the tests."""
    (tmp_path / 'a-file').write_text('')
    directory = tmp_path / 'a-file' / 'fastcat'
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(directory))
    return directory


def test_an_unwritable_directory_is_reported_and_no_db_is_given_out(isolated_store, blocked):
    with pytest.raises(RuntimeError, match='cannot write to its data directory .*FASTCAT_DATA_DIR'):
        FastCat(language='de')

    assert isolated_store.languages == {'en': 0}

    # English still works, since it needs nothing written
    assert _db_index(FastCat()) == 0


# --- moving the files fastcat 0.3.5 and earlier left in the package -------------

@pytest.fixture
def legacy(tmp_path, monkeypatch):
    """fastcat 0.3.5's package directory, and a separate data directory."""
    root = tmp_path / 'old-package'
    (root / 'data').mkdir(parents=True)
    (root / 'settings').mkdir()
    monkeypatch.setattr(paths, 'LEGACY_DIR', str(root))
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path / 'cache'))
    return root


def _old_mapping(legacy, mapping):
    (legacy / 'settings' / 'redis_ids.pickle').write_bytes(pickle.dumps(mapping))


def _new_mapping(tmp_path, mapping=None):
    path = tmp_path / 'cache' / 'redis_ids.pickle'

    if mapping is not None:
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(pickle.dumps(mapping))

    return pickle.loads(path.read_bytes()) if path.exists() else None


def _old_dumps(legacy):
    for name in DUMP_NAMES:
        (legacy / 'data' / name).write_bytes(b'old ' + name.encode())


def test_the_old_mapping_is_moved(isolated_store, legacy, tmp_path, capsys):
    _old_mapping(legacy, {'en': 0, 'de': 1, 'pl': 2})

    f = FastCat(language='pl')

    assert _db_index(f) == 2
    assert _new_mapping(tmp_path) == {'en': 0, 'de': 1, 'pl': 2}
    assert not (legacy / 'settings').exists()
    assert 'Moved the language -> Redis db mapping' in capsys.readouterr().out


def test_the_old_dumps_are_moved_and_other_files_left_alone(isolated_store, legacy, tmp_path):
    _old_dumps(legacy)
    (legacy / 'data' / 'notes.txt').write_text('mine')

    FastCat()

    for name in DUMP_NAMES:
        assert (tmp_path / 'cache' / name).read_bytes() == b'old ' + name.encode()
    assert os.listdir(legacy / 'data') == ['notes.txt']


def test_a_moved_dump_is_loaded_without_downloading_it(isolated_store, legacy, monkeypatch):
    (legacy / 'data' / 'skos-wiki-archive-et.nt.bz2').write_bytes(bz2.compress(
        b'<http://et.dbpedia.org/resource/Kategooria:Tallinn> '
        b'<http://www.w3.org/2004/02/skos/core#broader> '
        b'<http://et.dbpedia.org/resource/Kategooria:Eesti_linnad> .\n'))
    monkeypatch.setattr(FastCat, '_download', lambda *args: pytest.fail('downloaded'))
    client = FakeRedis()
    FastCat(db=client, language='et').load(progress_bar=False)

    assert client.sets['b:Tallinn'] == {'Eesti linnad'}
    assert not (legacy / 'data').exists()


def test_a_dump_already_in_the_data_directory_wins(isolated_store, legacy, tmp_path, capsys):
    _old_dumps(legacy)
    (tmp_path / 'cache').mkdir()
    for name in DUMP_NAMES:
        (tmp_path / 'cache' / name).write_bytes(b'new')

    FastCat()

    for name in DUMP_NAMES:
        assert (tmp_path / 'cache' / name).read_bytes() == b'new'
    assert not (legacy / 'data').exists()
    assert 'Moving' not in capsys.readouterr().out


@pytest.mark.parametrize('old, new, merged', [
    ({'en': 0, 'de': 1}, {'en': 0, 'de': 1, 'pl': 2}, {'en': 0, 'de': 1, 'pl': 2}),
    ({'en': 0, 'ru': 3}, {'en': 0, 'de': 1}, {'en': 0, 'de': 1, 'ru': 3}),
], ids=['already-there', 'merged'])
def test_two_mappings_that_agree_are_merged(isolated_store, legacy, tmp_path, old, new, merged):
    _old_mapping(legacy, old)
    _new_mapping(tmp_path, new)

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        FastCat()

    assert isolated_store.languages == merged
    assert _new_mapping(tmp_path) == merged
    assert not (legacy / 'settings').exists()


@pytest.mark.parametrize('old', [{'en': 0, 'pl': 1}, {'en': 0, 'de': 2}],
                         ids=['one-db-two-languages', 'one-language-two-dbs'])
def test_two_mappings_that_disagree_are_reported(isolated_store, legacy, tmp_path, old):
    _old_mapping(legacy, old)
    _new_mapping(tmp_path, {'en': 0, 'de': 1})

    with pytest.warns(RuntimeWarning, match='mappings that disagree.*en db 0, de db 1'):
        f = FastCat(language='de')

    # The data directory's mapping is used, and nothing is lost
    assert _db_index(f) == 1
    assert _new_mapping(tmp_path) == {'en': 0, 'de': 1}
    assert (legacy / 'settings' / 'redis_ids.pickle').exists()


def test_if_nothing_can_be_moved_the_old_mapping_is_still_used(isolated_store, legacy, tmp_path,
                                                               monkeypatch):
    _old_mapping(legacy, {'en': 0, 'pl': 1})
    _old_dumps(legacy)
    (tmp_path / 'a-file').write_text('')
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path / 'a-file' / 'fastcat'))

    with pytest.warns(RuntimeWarning) as caught:
        f = FastCat(language='pl')

    assert _db_index(f) == 1
    assert [str(w.message) for w in caught if 'mapping' in str(w.message)]
    assert [str(w.message) for w in caught if 'dumps' in str(w.message)]
    assert (legacy / 'settings' / 'redis_ids.pickle').exists()
    assert sorted(os.listdir(legacy / 'data')) == sorted(DUMP_NAMES)


def _next_process(monkeypatch):
    monkeypatch.setattr(interface, '_legacy_dumps_checked', False)


def test_on_another_filesystem_files_are_copied_and_the_originals_kept(
        isolated_store, legacy, tmp_path, monkeypatch, capsys):
    # The package directory may be a volume that outlasts the data directory,
    # as in docker-compose.yml up to 0.3.5: moving would empty it for good
    monkeypatch.setattr(paths, 'same_filesystem', lambda path, other: False)
    _old_mapping(legacy, {'en': 0, 'pl': 1})
    _old_dumps(legacy)

    FastCat()

    assert _new_mapping(tmp_path) == {'en': 0, 'pl': 1}
    for name in DUMP_NAMES:
        assert (tmp_path / 'cache' / name).read_bytes() == b'old ' + name.encode()
    assert sorted(os.listdir(legacy / 'data')) == sorted(DUMP_NAMES)
    assert (legacy / 'settings' / 'redis_ids.pickle').exists()
    out = capsys.readouterr().out
    assert 'Copied the language -> Redis db mapping' in out
    assert 'Copying 2 cached dump(s)' in out
    assert 'FASTCAT_DATA_DIR' in out

    # Nothing to copy the next time, and nothing to say
    _next_process(monkeypatch)

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        assert _db_index(FastCat(language='pl')) == 1

    assert capsys.readouterr().out == ''
    assert sorted(os.listdir(legacy / 'data')) == sorted(DUMP_NAMES)


def test_a_read_only_package_directory_is_copied_from_once(isolated_store, legacy, tmp_path,
                                                           monkeypatch, capsys):
    rename, remove = os.replace, os.remove

    def no_renaming(source, destination):
        if str(source).startswith(str(legacy)):
            raise PermissionError(errno.EACCES, 'Permission denied')
        return rename(source, destination)

    def no_removing(path):
        if str(path).startswith(str(legacy)):
            raise PermissionError(errno.EACCES, 'Permission denied')
        return remove(path)

    monkeypatch.setattr(os, 'replace', no_renaming)
    monkeypatch.setattr(os, 'remove', no_removing)
    _old_mapping(legacy, {'en': 0, 'pl': 1})
    _old_dumps(legacy)

    FastCat()

    assert _new_mapping(tmp_path) == {'en': 0, 'pl': 1}
    assert sorted(os.listdir(tmp_path / 'cache')) == sorted(DUMP_NAMES + ['redis_ids.pickle'])
    assert 'Moving 2 cached dump(s)' in capsys.readouterr().out

    # The next process finds the copies, and has nothing to say
    _next_process(monkeypatch)

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        FastCat()

    assert capsys.readouterr().out == ''
    assert sorted(os.listdir(legacy / 'data')) == sorted(DUMP_NAMES)
