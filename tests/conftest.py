"""Shared fixtures and integration-test gating.

Category lookups need a Redis server *and* a SKOS dump downloaded from DBpedia
(~40 MB per language), so those tests are marked ``integration`` and skipped
unless ``--run-integration`` is given. Everything else runs offline in
milliseconds.
"""

import pytest

import fastcat
import fastcat.interface as interface
import fastcat.paths as paths


def pytest_addoption(parser):
    parser.addoption(
        '--run-integration',
        action='store_true',
        default=False,
        help='run tests that need a Redis server and download SKOS dumps from DBpedia',
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption('--run-integration'):
        return

    skip_integration = pytest.mark.skip(
        reason='needs --run-integration (Redis server + DBpedia download)')
    for item in items:
        if 'integration' in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture(scope='session')
def loaded_fastcat():
    """Return a factory giving a FastCat with its language loaded into Redis.

    Session-scoped and memoised: loading a language costs a download plus a few
    million Redis writes, so it must happen at most once per language per run.
    """
    clients = {}

    def _for_language(language):
        if language not in clients:
            client = fastcat.FastCat(language=language)
            client.load(progress_bar=False)
            clients[language] = client
        return clients[language]

    return _for_language


@pytest.fixture(autouse=True)
def isolated_files(request, monkeypatch):
    """Keep unit tests away from the real data and package directories.

    Each unit test gets tmp_path as its data directory, and an empty
    stand-in for the package directory, where fastcat 0.3.5 and earlier
    kept their files. Nothing then reads the developer's dumps and mapping,
    or warns about old ones. Integration tests use the real directories, so
    the dumps they download are cached across runs.
    """
    if request.node.get_closest_marker('integration'):
        return

    tmp_path = request.getfixturevalue('tmp_path')
    monkeypatch.setenv(paths.DATA_DIR_VARIABLE, str(tmp_path))
    monkeypatch.setattr(paths, 'LEGACY_DIR', str(tmp_path / 'legacy-package'))
    monkeypatch.setattr(interface, '_legacy_files_checked', False)


@pytest.fixture
def isolated_store(isolated_files, monkeypatch):
    """Start the language/slot store afresh, saved in the test's tmp_path.

    ``store`` keeps its mapping in a module-level global, so without this
    one test's slot assignments would leak into the next.
    """
    import fastcat.store as store

    monkeypatch.setattr(store, 'languages', {})
    store.load_settings()
    return store
