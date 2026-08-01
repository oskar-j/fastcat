# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/oskar-j/fastcat/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/oskar-j/fastcat/compare/v_01_2...v0.2.0
[0.1.2]: https://github.com/oskar-j/fastcat/releases/tag/v_01_2
[0.1.0]: https://github.com/oskar-j/fastcat/releases
