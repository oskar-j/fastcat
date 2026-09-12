# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.4] - 2026-09-12

### Changed

- `load()` is roughly 20x faster. Redis writes are pipelined instead of issuing
  two blocking round-trips per triple: loading Czech went from **91.5s to 4.2s**
  on the same machine, and English from minutes to **58s** for its 1.84M keys.
  The resulting data is byte-identical -- verified by hashing every key and
  member of a language loaded both ways.
- `load()` streams the dump instead of reading it into memory. It previously
  called `readlines()` on the whole decompressed file, which for English is
  1.05 GB of text and peaked at **1.26 GB of RSS**; a full English load now
  peaks at **58 MB**.
- The progress bar redraws only when it would visibly change, rather than once
  per line -- 6 million terminal writes were on the hot path for English.

### Added

- `batch_size` parameter on `load()` (default 10000 commands per pipeline
  flush), for trading memory against speed. Values below 1 raise `ValueError`.
- Offline tests for the load path, using a stand-in Redis client, covering
  triple parsing, batching behaviour and the ordering of the `loaded-skos`
  flag. This path previously had no coverage outside the integration tests.

## [0.2.3] - 2026-08-02

### Fixed

- `load()` works again. Every download URL returned 404 because DBpedia retired
  the `downloads.dbpedia.org/current/` tree; dumps are now fetched from the
  archived 2016-10 release, whose URLs are stable. Fixes #14.

### Added

- `engine` parameter on `FastCat()` and `load()`, selecting where dumps come
  from. `'wiki-archive'` (the default) downloads the archived DBpedia 2016-10
  release; `'databus'` is recognised but raises `NotImplementedError` until the
  Databus resolver is written.
- `FastCat.get_supported_engines()` and `FastCat.get_implemented_engines()`.
- `fastcat.engines` module, with the engine names exported from the package
  root as `fastcat.WIKI_ARCHIVE`, `fastcat.DATABUS` and `fastcat.DEFAULT_ENGINE`.
- A failed download now raises `RuntimeError` naming the URL and engine,
  instead of a bare `HTTPError`, and no longer leaves a truncated file behind
  that would break the next `load()`.

### Changed

- **Data vintage:** categories now come from a 2016 snapshot of Wikipedia
  rather than a rolling current release. Relations added to Wikipedia after
  2016 are not present. This is the trade-off for having a working, stable
  download; the `databus` engine is the path back to current data.
- Dump parsing no longer branches on language. Archived dumps are plain
  n-triples for every language, and both the triple and quad shapes are now
  accepted, so English is no longer a special case.
- Cached dumps are named `skos-<engine>-<language>.nt.bz2`, so dumps from
  different engines cannot overwrite each other. Any previously downloaded file
  is ignored and re-fetched once.

## [0.2.2] - 2026-08-01

### Added

- [uv](https://docs.astral.sh/uv/) support: a committed `uv.lock`, a
  `.python-version` pinning the project interpreter, and a `dev` dependency
  group (PEP 735) so `uv sync && uv run pytest` works with no extra flags.
- CI job running `uv lock --check` and the suite from the locked environment,
  so the lockfile cannot drift from `pyproject.toml` unnoticed.

### Changed

- Oskar Jarczyk is now listed as an author as well as the maintainer.
- Dev dependencies are declared both as the `dev` extra (for pip) and as the
  `dev` dependency group (for uv); the two must be kept in step.

## [0.2.1] - 2026-08-01

### Added

- Automated PyPI release: merging to `master` builds, checks and publishes the
  package, then tags the commit and creates a GitHub release. Publishing uses
  PyPI trusted publishing (OIDC), so no API token is stored in the repository.
  Runs where the version in `pyproject.toml` is already on PyPI stop early
  instead of failing, so a merge without a version bump is a no-op.
- README badges for the PyPI version, supported Python versions and licence.

### Changed

- Downloads badge now points at `static.pepy.tech`, pepy's current endpoint.

### Removed

- The requires.io badge. The service has shut down and served an HTML lander
  instead of an image, so the badge rendered as a broken image.

## [0.2.0] - 2026-08-01

### Added

- `Dockerfile` and `docker-compose.yml` providing a dockerized Redis (plus a
  container to run the suite in), so no local Redis install is needed.
- `FASTCAT_REDIS_HOST` / `FASTCAT_REDIS_PORT` environment variables for pointing
  fastcat at a non-local Redis without passing connection arguments.
- `CHANGELOG.md` (this file).
- `requirements-dev.txt`, mirroring the new `dev` extra.
- GitHub Actions workflow covering Python 3.10-3.14, a packaging check
  (`python -m build` + `twine check`) and a manually triggered integration job.
- Offline unit tests for language normalisation, DBpedia URL parsing and Redis
  db-slot bookkeeping — the suite no longer needs a network round-trip to catch
  a broken language definition.
- `fastcat.__version__`.

### Changed

- **Breaking:** dropped Python 3.5-3.9; the minimum supported version is now
  3.10.
- Moved the package to a `src/` layout (`src/fastcat/`) and the tests out of the
  distributed package into a top-level `tests/` directory.
- Replaced `setup.py`/`setup.cfg` with a PEP 621 `pyproject.toml`.
- Migrated the test suite from `unittest`/`nosetests` to `pytest`: the nine
  per-language `TestCase` classes are now one parametrized module backed by
  fixtures in `conftest.py`. Tests needing Redis and a DBpedia download are
  marked `integration` and skipped unless `--run-integration` is passed.
- Pinned dependency ranges (`redis>=5.0.0,<8.0.0`, `pycountry>=24.6.1,<26.0.0`)
  instead of unbounded requirements.
- Replaced the hardcoded Redis option dict with the client's own defaults, so
  fastcat no longer passes arguments (`charset`, `errors`) that recent
  redis-py releases removed.

### Fixed

- Connection arguments (`host`, `port`, ...) were silently dropped for every
  language other than English, and by `switch_language()`; all connections now
  reuse the options given to the constructor.

### Removed

- Travis CI configuration, superseded by GitHub Actions.

## [0.1.2] - 2019

### Added

- Czech language support.
- Estonian, Russian and Ukrainian language support.
- Downloads badge and project logo in the README.

## [0.1.0] - 2019

### Added

- Initial release of this fork of [edsu/fastcat](https://github.com/edsu/fastcat):
  port to Python 3, support for more than one language (English, German,
  Japanese, Polish, Portuguese), and publication to PyPI.

[Unreleased]: https://github.com/oskar-j/fastcat/compare/v0.2.4...HEAD
[0.2.4]: https://github.com/oskar-j/fastcat/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/oskar-j/fastcat/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/oskar-j/fastcat/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/oskar-j/fastcat/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/oskar-j/fastcat/compare/v_01_2...v0.2.0
[0.1.2]: https://github.com/oskar-j/fastcat/releases/tag/v_01_2
[0.1.0]: https://github.com/oskar-j/fastcat/releases
