"""Offline checks on where fastcat keeps its files (#33).

Up to 0.3.5 the dumps and the language -> db mapping lived inside the
installed package, and ``import fastcat`` created the directories for them,
so a read-only install could not even be imported. They now go to the
user's cache directory (or ``FASTCAT_DATA_DIR``), created when the first
file is written. 0.3.6 moved the files an earlier version left in the
package; since 0.4.0 ``FastCat()`` only warns about them.

conftest points the data directory at tmp_path, and the package directory
at an empty tmp_path/legacy-package, for every test.
"""

import os
import pickle
import shutil
import subprocess
import sys
import warnings

import pytest

import fastcat.interface as interface
import fastcat.paths as paths
from fastcat.interface import FastCat

PACKAGE = os.path.dirname(os.path.realpath(interface.__file__))

DUMP_NAMES = ['skos-wiki-archive-de.nt.bz2', 'skos-databus-et.nt.bz2']


def _db_index(f):
    return f.db.connection_pool.connection_kwargs.get('db', 0)


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


# --- files fastcat 0.3.5 and earlier left in the package -----------------------
#
# 0.3.6 moved them to the data directory. 0.4.0 doesn't, but says what it found.

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


def _old_dumps(legacy):
    for name in DUMP_NAMES:
        (legacy / 'data' / name).write_bytes(b'old ' + name.encode())


def _snapshot(*roots):
    return {str(root): _listing(root) for root in roots if root.exists()}


def test_an_old_mapping_is_reported_and_neither_used_nor_moved(isolated_store, legacy, tmp_path):
    _old_mapping(legacy, {'en': 0, 'et': 1, 'pl': 2})
    _old_dumps(legacy)
    before = _snapshot(legacy)

    with pytest.warns(RuntimeWarning) as caught:
        f = FastCat(language='pl')

    message = str(caught[0].message)
    assert str(legacy) in message
    for name in ['settings/redis_ids.pickle'] + ['data/' + name for name in DUMP_NAMES]:
        assert os.path.join(*name.split('/')) in message
    assert str(tmp_path / 'cache') in message
    assert 'fastcat 0.3.6' in message
    assert 'mapping in there is ignored' in message

    # A fresh mapping, so Polish gets the next db rather than its old one
    assert _db_index(f) == 1
    assert _snapshot(legacy) == before
    assert sorted(os.listdir(tmp_path / 'cache')) == ['redis_ids.pickle']


def test_old_dumps_alone_are_reported_as_harmless(isolated_store, legacy):
    _old_dumps(legacy)

    with pytest.warns(RuntimeWarning, match='downloaded again') as caught:
        FastCat()

    assert 'mapping in there is ignored' not in str(caught[0].message)


def test_an_old_mapping_next_to_a_current_one_is_reported_as_harmless(isolated_store, legacy,
                                                                      tmp_path):
    # What 0.3.6 left when it copied the files across filesystems
    _old_mapping(legacy, {'en': 0, 'pl': 1})
    (tmp_path / 'cache').mkdir()
    (tmp_path / 'cache' / 'redis_ids.pickle').write_bytes(pickle.dumps({'en': 0, 'pl': 1}))

    with pytest.warns(RuntimeWarning, match='delete them') as caught:
        f = FastCat(language='pl')

    assert 'mapping in there is ignored' not in str(caught[0].message)
    assert _db_index(f) == 1


def test_the_warning_comes_once_per_process(isolated_store, legacy):
    _old_dumps(legacy)

    with pytest.warns(RuntimeWarning):
        FastCat()

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        FastCat()
        FastCat(language='de')


@pytest.mark.parametrize('leftover', ['nothing', 'empty folders', 'other files'])
def test_nothing_of_fastcats_is_not_reported(isolated_store, legacy, leftover):
    if leftover == 'nothing':
        shutil.rmtree(legacy)
    elif leftover == 'other files':
        (legacy / 'data' / 'notes.txt').write_text('mine')
        (legacy / 'data' / 'skos-wiki-archive-en.nt.bz2.0123456789ab.part').write_bytes(b'')

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        FastCat()
