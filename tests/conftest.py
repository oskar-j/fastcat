"""Shared fixtures and integration-test gating.

Category lookups need a Redis server *and* a SKOS dump downloaded from DBpedia
(~40 MB per language), so those tests are marked ``integration`` and skipped
unless ``--run-integration`` is given. Everything else runs offline in
milliseconds.
"""

import pytest

import fastcat


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


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    """Point the language/slot store at a throwaway pickle file.

    ``store`` keeps its mapping in a module-level global backed by a pickle
    inside the package directory; without this the unit tests would clobber the
    developer's real slot assignments.
    """
    import fastcat.store as store

    monkeypatch.setattr(store, 'settings_filename', str(tmp_path / 'redis_ids.pickle'))
    monkeypatch.setattr(store, 'languages', {})
    store.load_settings()
    return store
