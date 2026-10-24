# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.5] - 2026-10-24

### Fixed

- `switch_language()` keeps the connection's settings. It used to rebuild
  the client from the constructor's keyword arguments. A client passed in as
  `db` leaves those empty, so the object reconnected to `localhost:6379`
  without that client's password, SSL or socket. For a language with no db
  yet, it then downloaded the dump and loaded it into whatever Redis ran
  there. The new client now comes from the current one's connection pool,
  so it reaches the same server with the same settings
  ([#28](https://github.com/oskar-j/fastcat/issues/28)).
- `get_current_language()` reports Ukrainian as `'Ukrainian'`, not
  `'Ukraine'`. Languages are now looked up in pycountry by their ISO 639-1
  code (`uk`) rather than fastcat's id (`ua`, the country code). If your code
  reads `.alpha_2`, note that it is now `'uk'`, where it used to be `'UA'`.
  An id pycountry doesn't know gives `None` instead of an `IndexError`
  ([#30](https://github.com/oskar-j/fastcat/issues/30)).
- fastcat installs alongside redis-py 8 and pycountry 26. The caps are now
  `redis<9` and `pycountry<27`. The test suite passes on the lowest
  versions allowed (redis 5.0.0, pycountry 24.6.1) and the newest (redis
  8.1.0, pycountry 26.2.16), and the integration tests pass against a real
  Redis on redis-py 8.1
  ([#29](https://github.com/oskar-j/fastcat/issues/29)).

## [0.3.4] - 2026-10-24

### Fixed

- The `databus` engine works again. The Databus has been cutting its release
  metadata short (about 65 KB of 384 KB), so no dump could be found for any
  language, and the error escaped as a bare `http.client.IncompleteRead`.
  fastcat now looks each dump up through the Databus SPARQL endpoint, which
  answers in a few hundred bytes. It falls back to the release metadata only
  if that fails, and a response cut short is retried like any other network
  error ([#26](https://github.com/oskar-j/fastcat/issues/26)).
- An interrupted download no longer breaks every later `load()`.
  - **Before:** Ctrl-C, a dropped connection or a stalled transfer left a
    partial dump in the cache, which `load()` then trusted for good.
  - **Now:** downloads go to a temporary file, which takes the dump's name
    only once it is complete and, for the Databus, matches its checksum. A
    download that receives nothing for 60 seconds is given up, and a failed
    one leaves nothing in the cache.
  - **Already damaged:** a damaged dump left in the cache by an earlier
    version is deleted when `load()` reaches the damage, with a
    `DamagedDumpError` (a `RuntimeError`), so the next `load()` downloads it
    again ([#27](https://github.com/oskar-j/fastcat/issues/27)).

### Added

- `fastcat.engines.databus_sparql_source()` looks a dump up through the
  Databus SPARQL endpoint.
- `fastcat.interface.DamagedDumpError`, and `DOWNLOAD_TIMEOUT` (seconds
  without data before a download is given up, default 60).

## [0.3.3] - 2026-10-23

### Added

- `load()` records which language filled a db (`loaded-language`, next to
  `loaded-engine`) and refuses to load another language on top, with a
  `RuntimeError` naming both. Previously that load was skipped as "already
  loaded", leaving the new language's lookups answered from the old one. Data
  loaded before this release carries no marker and is treated as before.
- `FastCat.language`: the id of the language the object works in.

### Fixed

- `FastCat(db=client, language='et')` honours the language. It used to be
  ignored whenever a client was passed, so `load()` looked the client's db
  number up in the slot store instead: an unassigned db raised
  `AttributeError: 'NoneType' object has no attribute 'alpha_2'`, and a db the
  store assigns to another language would have been filled with that
  language. `get_current_language()` now reports the language given, too
  ([#23](https://github.com/oskar-j/fastcat/issues/23)).
- `load()` with no language to go on (your own client, no `language=`, on a db
  no language is assigned to) raises a `ValueError` saying how to name one.

## [0.3.2] - 2026-10-23

There is no 0.3.1: that version number was planned for the README refresh,
which was merged without a release, so it ships here instead.

### Added

- `fastcat.utils.resolve_language()`: normalises a language code like
  `normalize_language()`, but raises a `ValueError` naming the supported
  languages instead of returning `None`.

### Changed

- The package summary on PyPI is now "Wikipedia's category graph in your own
  Redis: load a DBpedia dump once, then look up broader and narrower
  categories locally, without the Wikipedia API.", matching the GitHub
  description.

### Fixed

- `uk`, Ukrainian's ISO 639-1 language code and DBpedia subdomain, is
  accepted wherever a language is (as are `uk-UA` and `uk_UA`). It means
  Ukrainian, not the United Kingdom: like every fastcat code it is a language
  code, and English stays `en`. fastcat's own id for Ukrainian is still `ua`
  (Ukraine's country code), so existing data and slot assignments are
  untouched ([#22](https://github.com/oskar-j/fastcat/issues/22)).
- An unrecognised language raises a `ValueError` before anything is written.
  It used to be given a Redis db under the name `None`, saved to the settings
  pickle for good, and `load()` then failed with a bare `LookupError`; later
  unrecognised codes silently shared that db. A `None` entry already in a
  pickle stays there, but nothing can reach it any more
  ([#22](https://github.com/oskar-j/fastcat/issues/22)).
- `switch_language()` and `load(language=...)` accept the same spellings as
  the constructor (`pt-BR`, `ger`, `uk`). They used the code as given, which
  failed further in: at the category-prefix lookup, or with a download for a
  language that does not exist.

### Documentation

- README refreshed. The cat logo is replaced by a banner, in light and dark
  variants that follow the reader's system theme, drawn from fastcat's own
  output: the English dump, what `load()` makes of it in Redis, and the two
  sets `broader()` and `narrower()` read for "Computer programming".
- Every usage example was re-run against a real Redis. Two were wrong and are
  fixed: the Databus examples called `FastCat(engine='databus').load(language='et')`,
  which loads Estonian into the English db (and raises if English is already
  there), and the German example showed 5 of the 31 categories under `Berlin`
  as if they were all of them.
- New sections: a quick start, connecting to Redis (keyword arguments, the
  `FASTCAT_REDIS_*` variables, passing your own client), the `load()`
  arguments, where dumps are cached, and a table of supported languages with
  the codes each one accepts.
- Install instructions brought up to date: `brew services start redis`, WSL or
  Docker instead of the retired Windows port, `docker run` for pip users, and
  `uv add fastcat`.
- Two new badges, `uv` and last commit; links moved to https.

## [0.3.0] - 2026-09-12

### Added

- **The `databus` engine is implemented.** `FastCat(engine='databus')` now
  downloads current category data from DBpedia's
  [Databus](https://databus.dbpedia.org/) instead of the 2016 archive. Files
  there have no fixed URLs, so the engine resolves the newest version of the
  `generic/categories` artifact and picks the `skos` part for the language.
  All nine supported languages are available (138 in total on the Databus).
- Downloads are verified against the sha256 the Databus publishes for each
  file; a mismatch discards the file and raises. The wiki archive publishes no
  checksums, so nothing changes there.
- `databus_source()`, `latest_databus_version()`, `databus_parts()` and
  `skos_source()` in `fastcat.engines`, plus `clear_cache()` for the metadata
  cache. `skos_source()` returns the URL and checksum together; `skos_url()`
  remains as a thin wrapper.
- Databus metadata lookups retry transient failures (3 attempts) rather than
  failing a whole load -- a real blip was seen while developing this.
- `load()` records which engine populated a Redis db, and refuses to load one
  engine's data on top of the other's, which would merge two different
  snapshots of Wikipedia into relations belonging to neither. Flush the db (or
  use another) to switch engines. Data loaded before 0.3.0 counts as
  wiki-archive, which is what it was.

### Changed

- `engine='databus'` no longer raises `NotImplementedError`.
- The two engines return genuinely different data, which is the point. Estonian
  is 31,678 keys from the 2016 archive and 41,254 from the Databus, and
  relations differ: `broader("Tallinn")` gives `['Eesti linnad', 'Harju
  maakonna omavalitsused', 'Hansalinnad']` from the 2016 archive and
  `['Eesti asulate kategooriad', 'Harju maakonna omavalitsusüksuste
  kategooriad']` from the 2022.12.01 release.

`wiki-archive` remains the default: it needs no metadata lookup, cannot be
affected by the Databus being down, and keeps existing installs on the data
they already have. Pass `engine='databus'` for current categories.

## [0.2.5] - 2026-09-12

### Changed

- Release workflow moved off actions still running on Node.js 20, which GitHub
  now forces onto Node.js 24 with a deprecation warning on every run:
  `actions/upload-artifact` v4 -> v7 and `actions/download-artifact` v4 -> v8.
  Node.js 24 became the default in upload-artifact v6 and download-artifact v7,
  so the earlier majors would not have cleared the warning.

No library code changed in this release; it is packaging and CI only.

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

[Unreleased]: https://github.com/oskar-j/fastcat/compare/v0.3.5...HEAD
[0.3.5]: https://github.com/oskar-j/fastcat/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/oskar-j/fastcat/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/oskar-j/fastcat/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/oskar-j/fastcat/compare/v0.3.0...v0.3.2
[0.3.0]: https://github.com/oskar-j/fastcat/compare/v0.2.5...v0.3.0
[0.2.5]: https://github.com/oskar-j/fastcat/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/oskar-j/fastcat/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/oskar-j/fastcat/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/oskar-j/fastcat/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/oskar-j/fastcat/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/oskar-j/fastcat/compare/v_01_2...v0.2.0
[0.1.2]: https://github.com/oskar-j/fastcat/releases/tag/v_01_2
[0.1.0]: https://github.com/oskar-j/fastcat/releases
