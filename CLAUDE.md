# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`fastcat` is a small Python 3 library that loads DBpedia's SKOS category dumps (derived from Wikipedia MySQL dumps) into a local Redis instance so broader/narrower category lookups can be done locally instead of hitting the Wikipedia API. It is a fork of [edsu/fastcat](https://github.com/edsu/fastcat), ported to Python 3 with multi-language support.

## Commands

`src/` layout, PEP 621 metadata in `pyproject.toml`, Python >= 3.10.

```
pip install -e '.[dev]'
pytest                                       # fast offline tests only
pytest tests/test_names.py::test_percent_encoding_is_decoded   # one test
```

Anything touching Redis or DBpedia is marked `integration` and skipped unless opted in:

```
docker compose up -d redis                   # dockerized Redis on localhost:6379
pytest --run-integration                     # very slow: ~40 MB download per language
pytest --run-integration "tests/test_categories.py::test_broader[pl]"   # one language
```

Integration runs are slow the first time because `FastCat.load()` downloads a bz2 SKOS dump per language and inserts every triple into Redis; later runs short-circuit on the `loaded-skos` key. `docker compose run --rm fastcat pytest` runs the suite inside a container instead (`FASTCAT_REDIS_HOST`/`FASTCAT_REDIS_PORT` point fastcat at the Redis service). `sample.py` is a scratch script for manual end-to-end checks.

**Note (as of 2026-08-01): the DBpedia download URLs in `_download()` return 404** — `downloads.dbpedia.org/current/core/...` no longer serves those files. Integration tests cannot pass until the URLs are updated to the current DBpedia Databus layout. Unit tests are unaffected.

There is no linter configured. CI is GitHub Actions (`.github/workflows/tests.yml`): unit tests on 3.10-3.14, a `python -m build` + `twine check` job, and a manual-only integration job.

## Architecture

Four modules under `fastcat/`, with `FastCat` (in `interface.py`) as the single public entry point re-exported by `__init__.py`.

**Redis db slot per language.** Redis exposes 16 numbered databases, so fastcat stores each language in its own db index — hence the hard cap of 16 languages. The language→slot map lives in a module-global dict in `store.py`, pickled to `src/fastcat/settings/redis_ids.pickle` (i.e. inside the package directory — the `isolated_store` fixture redirects it so unit tests don't clobber real slot assignments). `en` is always slot 0. `store.load_settings()` must run before slot lookups (the `FastCat.__init__` does this); `save_settings()` allocates the next free slot and re-pickles. `get_slot()` raises `ValueError` for an unknown language, and callers treat that as "allocate a new slot".

**Data model.** Keys are `b:<category>` (set of broader categories) and `n:<category>` (set of narrower ones), written as a pair for every `skos:core#broader` triple. `loaded-skos` is a per-db sentinel meaning "this language is populated" — note `_is_loaded()` ignores its `language` argument and just checks the current db.

**Language handling is spread across three places** — adding a language means editing all of them:
1. `src/fastcat/lang.py` — an entry in `available_languages` (`id` = ISO 639-1, `locales`, `alternate` = ISO 639-2, `wikipedia_mapping` = DBpedia subdomain).
2. `src/fastcat/interface.py::FastCatBase._name()` — a per-language regex, because each DBpedia locale uses a translated category prefix (`Category:`, `Kategorie:`, `Kategoria:`, `Категория:`, …). Unhandled languages raise `NotImplementedError`.
3. `tests/language_cases.py` — a `LanguageCase` with a known broader/narrower pair (drives the parametrized integration tests), plus a URL case in `tests/test_names.py`, whose `test_every_supported_language_has_a_name_branch` fails if you skip step 2.

`utils.normalize_language()` maps any of the three forms (id, locale, ISO 639-2) down to the `id`; it returns `None` for unknown input rather than raising.

**English is a special case throughout.** It downloads from `core/skos_categories_en.ttl.bz2` (3-term n-triples, `ntriple_pattern`); all other languages come from `core-i18n/<mapping>/skos_categories_<mapping>.tql.bz2` (4-term quads, `ntriple_pattern_wide`).

**`id` and `wikipedia_mapping` are not always the same.** Ukrainian is `id='ua'` (the key used in the pickle and by callers) but `wikipedia_mapping='uk'` (the DBpedia subdomain and the actual ISO code). `store.get_language()` carries a pycountry fallback that searches *countries* by alpha-2 when a language lookup misses — that fallback exists for cases like this.

Downloads land in `src/fastcat/data/skos-<lang>.nt.bz2`; both `data/` and `settings/` are created at import time in `interface.py` and are gitignored. Writing state into the package directory is a known wart — see the README's "What's coming next?".
