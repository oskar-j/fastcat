# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`fastcat` is a small Python 3 library that loads DBpedia's SKOS category dumps (derived from Wikipedia MySQL dumps) into a local Redis instance so broader/narrower category lookups can be done locally instead of hitting the Wikipedia API. It is a fork of [edsu/fastcat](https://github.com/edsu/fastcat), ported to Python 3 with multi-language support.

## Commands

`src/` layout, PEP 621 metadata in `pyproject.toml`, Python >= 3.10.

```
uv sync && uv run pytest                     # uv path: installs from uv.lock
pip install -e '.[dev]' && pytest            # pip path
pytest tests/test_names.py::test_percent_encoding_is_decoded   # one test
```

Dev dependencies are declared **twice** in `pyproject.toml` — as the `dev` extra (pip) and as the `dev` dependency group (uv installs it by default). Changing one means changing the other, then re-running `uv lock`; CI's `uv` job runs `uv lock --check` and fails if `uv.lock` drifts from `pyproject.toml`.

Anything touching Redis or DBpedia is marked `integration` and skipped unless opted in:

```
docker compose up -d redis                   # dockerized Redis on localhost:6379
pytest --run-integration                     # very slow: ~40 MB download per language
pytest --run-integration "tests/test_categories.py::test_broader[pl]"   # one language
```

Integration runs are slow the first time because `FastCat.load()` downloads a bz2 SKOS dump per language (~45 MB for English) and inserts every triple into Redis; later runs short-circuit on the `loaded-skos` key. Since 0.2.4 `load()` pipelines its writes (`batch_size`, default 10000) and streams the dump instead of `readlines()`-ing it, so English takes ~58s and ~58 MB rather than minutes and 1.26 GB — keep both properties in mind before touching that loop. `docker compose run --rm fastcat pytest` runs the suite inside a container instead (`FASTCAT_REDIS_HOST`/`FASTCAT_REDIS_PORT` point fastcat at the Redis service). `sample.py` is a scratch script for manual end-to-end checks.

Downloads come from `src/fastcat/engines.py`. `wiki-archive` (the default) pulls DBpedia's archived **2016-10** release at `downloads.dbpedia.org/2016-10/core-i18n/<mapping>/skos_categories_<mapping>.ttl.bz2` — stable URLs, but the categories stop at 2016. `databus` resolves the newest version of the Databus artifact `dbpedia/generic/categories`, picks the part with `dcv:lang=<mapping>` and `dcv:tag=skos`, and verifies the published sha256 after downloading (metadata fetches are cached per process and retried 3x). The two engines are different Wikipedia snapshots, so `load()` records `loaded-engine` in the db and refuses to load one on top of the other; data written before 0.3.0 counts as wiki-archive. The old `current/` tree returns 404 for everything, which is what broke `load()` before 0.2.3 (#14).

There is no linter configured. CI is GitHub Actions (`.github/workflows/tests.yml`): unit tests on 3.10-3.14, a `python -m build` + `twine check` job, and a manual-only integration job.

**Releasing is automatic**: `.github/workflows/publish.yml` runs on every push to `master` and publishes to PyPI via trusted publishing (OIDC, `pypi` environment — no stored token), then tags the commit and cuts a GitHub release. It reads the version from `pyproject.toml` and skips the whole pipeline if that version is already on PyPI, so bumping `version` in `pyproject.toml` (plus a `CHANGELOG.md` entry) *is* the release action. Never `twine upload` by hand.

## Architecture

Four modules under `fastcat/`, with `FastCat` (in `interface.py`) as the single public entry point re-exported by `__init__.py`.

**Redis db slot per language.** Redis exposes 16 numbered databases, so fastcat stores each language in its own db index — hence the hard cap of 16 languages. The language→slot map lives in a module-global dict in `store.py`, pickled to `src/fastcat/settings/redis_ids.pickle` (i.e. inside the package directory — the `isolated_store` fixture redirects it so unit tests don't clobber real slot assignments). `en` is always slot 0. `store.load_settings()` must run before slot lookups (the `FastCat.__init__` does this); `save_settings()` allocates the next free slot and re-pickles. `get_slot()` raises `ValueError` for an unknown language, and callers treat that as "allocate a new slot".

**Data model.** Keys are `b:<category>` (set of broader categories) and `n:<category>` (set of narrower ones), written as a pair for every `skos:core#broader` triple. `loaded-skos` is a per-db sentinel meaning "this language is populated" — note `_is_loaded()` ignores its `language` argument and just checks the current db.

**Language handling is spread across three places** — adding a language means editing all of them:
1. `src/fastcat/lang.py` — an entry in `available_languages` (`id` = ISO 639-1, `locales`, `alternate` = ISO 639-2, `wikipedia_mapping` = DBpedia subdomain).
2. `src/fastcat/interface.py::FastCatBase._name()` — a per-language regex, because each DBpedia locale uses a translated category prefix (`Category:`, `Kategorie:`, `Kategoria:`, `Категория:`, …). Unhandled languages raise `NotImplementedError`.
3. `tests/language_cases.py` — a `LanguageCase` with a known broader/narrower pair (drives the parametrized integration tests), plus a URL case in `tests/test_names.py`, whose `test_every_supported_language_has_a_name_branch` fails if you skip step 2.

`utils.normalize_language()` maps any of the three forms (id, locale, ISO 639-2) down to the `id`; it returns `None` for unknown input rather than raising.

**English is no longer a special case** (it was before 0.2.3). Archived dumps are 3-term n-triples for every language, opening with a `# started ...` header line; `load()` tries `ntriple_pattern` then `ntriple_pattern_wide`, so the quad `.tql` flavour still parses if a future engine serves it.

**`id` and `wikipedia_mapping` are not always the same.** Ukrainian is `id='ua'` (the key used in the pickle and by callers) but `wikipedia_mapping='uk'` (the DBpedia subdomain and the actual ISO code). `store.get_language()` carries a pycountry fallback that searches *countries* by alpha-2 when a language lookup misses — that fallback exists for cases like this.

Downloads land in `src/fastcat/data/skos-<lang>.nt.bz2`; both `data/` and `settings/` are created at import time in `interface.py` and are gitignored. Writing state into the package directory is a known wart — see the README's "What's coming next?".
