fastcat
=======

[![Tests](https://github.com/oskar-j/fastcat/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/oskar-j/fastcat/actions/workflows/tests.yml)
[![Publish](https://github.com/oskar-j/fastcat/actions/workflows/publish.yml/badge.svg?branch=master)](https://github.com/oskar-j/fastcat/actions/workflows/publish.yml)
[![PyPI](https://img.shields.io/pypi/v/fastcat)](https://pypi.org/project/fastcat/)
[![Python Versions](https://img.shields.io/pypi/pyversions/fastcat)](https://pypi.org/project/fastcat/)
[![Downloads](https://static.pepy.tech/badge/fastcat)](https://pepy.tech/project/fastcat)
[![License](https://img.shields.io/badge/license-CC%20BY--SA%203.0-blue)](https://creativecommons.org/licenses/by-sa/3.0/)

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://docs.astral.sh/uv/)
[![Last Commit](https://img.shields.io/github/last-commit/oskar-j/fastcat)](https://github.com/oskar-j/fastcat/commits/master)
[![Commits Since Release](https://img.shields.io/github/commits-since/oskar-j/fastcat/latest)](https://github.com/oskar-j/fastcat/releases)
[![Pending Pull-Requests](https://img.shields.io/github/issues-pr/oskar-j/fastcat)](https://github.com/oskar-j/fastcat/pulls)
[![Github Issues](https://img.shields.io/github/issues/oskar-j/fastcat)](https://github.com/oskar-j/fastcat/issues)

Fastcat is a little Python library for quickly looking up broader/narrower
relations between Wikipedia categories, locally. The idea is that fastcat can be
useful in situations where you need to rapidly look up category relations,
but don't want to hammer on the [Wikipedia API](https://en.wikipedia.org/w/api.php).
Fastcat relies on Redis and the [SKOS files](https://downloads.dbpedia.org/2016-10/core-i18n/)
that DBpedia builds from the Wikipedia [dumps](https://dumps.wikimedia.org/enwiki/latest/): it loads a
language's dump into Redis once, and after that every hop up or down the
category graph is a single local lookup.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/oskar-j/fastcat/master/docs/banner-dark.svg">
  <img alt="fastcat: the 2016-10 English DBpedia dump loaded into Redis db 0, where &quot;Computer programming&quot; has 2 broader and 26 narrower categories" src="https://raw.githubusercontent.com/oskar-j/fastcat/master/docs/banner-light.svg" width="100%">
</picture>

*(The banner is drawn from fastcat's own output: the dump, the key counts and
both category sets are what `load()`, `broader()` and `narrower()` produce for
the English data.)*

Quick start
-----------

```
$ docker run -d --name redis -p 6379:6379 redis:7-alpine   # or any Redis on localhost:6379
$ pip install fastcat
```

```python
>>> import fastcat
>>> f = fastcat.FastCat()
>>> f.load()  # once: downloads ~45 MB from DBpedia and fills Redis, about a minute
>>> sorted(f.broader("Computer programming"))
['Software development', 'Software engineering']
```

Install
-------

### Redis

Fastcat needs a Redis server, by default on `localhost:6379`.

**On Mac:**

```
$ brew install redis
$ brew services start redis
```

**On Linux (Debian, Ubuntu):**

```
$ sudo apt install redis-server
```

**On Windows:**

Redis has no native Windows build. Either run it with Docker (below), or
install it inside [WSL](https://learn.microsoft.com/windows/wsl/install) with
the Linux instructions above.

**With Docker (any platform):**

```
$ docker run -d --name redis -p 6379:6379 redis:7-alpine
```

From a clone of this repository, the bundled compose file does the same and
keeps the loaded categories in a named volume, so they survive a restart:

```
$ docker compose up -d redis
```

### The module

```
$ pip install fastcat
```

Or with [uv](https://docs.astral.sh/uv/):

```
$ uv add fastcat
```

Or, for the newest development code:

```
$ pip install git+https://github.com/oskar-j/fastcat.git
```

Usage
-----

#### Basic usage

The first time you use fastcat you'll need to populate your Redis database
with the category data from DBpedia. To do that, create a `FastCat` object and
call its `load` method. After that you can use it to do lookups.

```python
>>> import fastcat
>>> f = fastcat.FastCat()
>>> f.load()  # downloads the dump and loads it into Redis (about a minute for English)
>>> sorted(f.broader("Computer programming"))
['Software development', 'Software engineering']
>>> len(f.narrower("Computer programming"))
26
>>> sorted(f.narrower("Computer programming"))[:6]
['Algorithms', 'Anti-patterns', 'Code refactoring', 'Computer libraries', 'Computer programmers', 'Computer programming books']
```

A few things worth knowing:

- Pass category names the way the category page title shows them, **without**
  the `Category:` prefix and with spaces rather than underscores.
- `broader()` and `narrower()` return a list built from a Redis set, so the
  order is arbitrary. Sort it if you need a stable one.
- An unknown category, or one with nothing above or below it, gives `[]`
  rather than an error.
- `load()` only has to run once per language. The data stays in Redis, and
  later calls print `Loading aborted (language already exists)` and return
  straight away.

Every answer is itself a category, so walking further is just more lookups.
For example, everything up to two levels above a category:

```python
>>> def ancestors(f, category, depth=2):
...     found, frontier = set(), {category}
...     for _ in range(depth):
...         frontier = {b for c in frontier for b in f.broader(c)} - found
...         found |= frontier
...     return found
...
>>> sorted(ancestors(f, "Computer programming"))
['Areas of computer science', 'Computer engineering', 'Computing', 'Engineering disciplines', 'Information technology management', 'Product development', 'Software', 'Software development', 'Software engineering', 'Systems engineering', 'Technology development']
```

Subtracting `found` matters: Wikipedia's category graph is not a tree, and a
category can turn up through more than one route (here `Software engineering`
is both a parent of `Computer programming` and of `Software development`).

#### Non-English categories

Pass a language code from the table below to the `FastCat()` constructor. Each
language is loaded into its own Redis database, so they don't mix.

```python
>>> import fastcat
>>> f = fastcat.FastCat(language='de')
>>> f.load()  # the German dump is smaller: about 10 seconds
>>> sorted(f.broader("Berlin"))
['Deutschland nach Bundesland', 'Deutschland nach Gemeinde', 'Europa nach Ort']
>>> len(f.narrower("Berlin"))
31
>>> sorted(f.narrower("Berlin"))[:4]
['Architektur (Berlin)', 'Berlin als Namensgeber', 'Berlin in der Kultur', 'Berlin nach Bezirk']
```

Category names are in the language of that Wikipedia, and again without its
prefix (`Kategorie:` for German).

##### Currently supported languages (and their codes)

| Language | Code | Also accepted | Prefix you leave off |
| --- | --- | --- | --- |
| Czech | `cs` | `cze` | `Kategorie:` |
| English | `en` | `eng`, `en-GB`, `en-US`, `en-CA`, `en-NZ` | `Category:` |
| Estonian | `et` | `est` | `Kategooria:` |
| German | `de` | `ger`, `de-DE` | `Kategorie:` |
| Japanese | `ja` | `jpn`, `ja-JP` | `Category:` |
| Polish | `pl` | `pol`, `pl-PL` | `Kategoria:` |
| Portuguese | `pt` | `por`, `pt-PT`, `pt-BR` | `Categoria:` |
| Russian | `ru` | `rus`, `ru-RU` | `Категория:` |
| Ukrainian | `ua` | `uk`, `ukr`, `uk-UA` | `Категорія:` |

Codes are case-insensitive, and `_` works in place of `-` (`pt_BR`). They are
language codes, not country codes, which is why Czech is `cs` rather than `cz`.
Ukrainian is the exception: its id in fastcat is `ua` (Ukraine's country code)
for historical reasons, but its language code `uk` works too. `uk` therefore
means Ukrainian, not the United Kingdom; British English is `en` or `en-GB`.
Any other code raises a `ValueError` that lists the supported ones.

#### Connecting to Redis

By default fastcat talks to `localhost:6379`. Any keyword argument the
constructor does not use itself is passed on to `redis.Redis`:

```python
>>> f = fastcat.FastCat(host='redis.example.com', port=6380, password='secret')
```

The `FASTCAT_REDIS_HOST` and `FASTCAT_REDIS_PORT` environment variables change
the default instead, which is how the `fastcat` service in `docker-compose.yml`
finds its Redis.

You can also hand fastcat a client of your own through `db`. It is used as it
is, whatever database it points at, and that database holds the language you
name:

```python
>>> import redis
>>> f = fastcat.FastCat(db=redis.Redis(db=15), language='et')
>>> f.load()
>>> f.get_current_language().name
'Estonian'
```

A database holds one language. fastcat records which one filled it, and
refuses to load another on top.

#### Where the data comes from

The `engine` argument selects the download source:

```python
>>> import fastcat
>>> f = fastcat.FastCat(engine='wiki-archive')  # the default
>>> f.load()
```

| Engine | Status | What it downloads |
| --- | --- | --- |
| `wiki-archive` | **default** | DBpedia's archived [2016-10 release](https://downloads.dbpedia.org/wiki-archive/dbpedia-version-2016-10.html): fixed URLs, data frozen in 2016 |
| `databus` | available | DBpedia's current [Databus](https://databus.dbpedia.org/) release (2022.12.01 at the time of writing): current data, resolved through metadata |

For up-to-date categories, ask for the Databus:

```python
>>> f = fastcat.FastCat(language='et', engine='databus')
>>> f.load()
```

The Databus has no fixed download URLs. fastcat resolves the newest version of
the `generic/categories` artifact, then asks the Databus SPARQL endpoint for the
SKOS part for your language, with the release's metadata page as a fallback. The
Databus also publishes a sha256 per file, which fastcat checks after
downloading; a mismatch discards the file rather than loading it.

##### The two engines are not interchangeable

They are different snapshots of Wikipedia, six years apart, and the categories
really do differ. For Estonian:

| Engine | `sorted(f.broader("Tallinn"))` | Category keys |
| --- | --- | --- |
| `wiki-archive` (2016) | `['Eesti linnad', 'Hansalinnad', 'Harju maakonna omavalitsused']` | 31,677 |
| `databus` (2022) | `['Eesti asulate kategooriad', 'Harju maakonna omavalitsusüksuste kategooriad']` | 41,252 |

Because mixing them would produce a set of relations belonging to neither
snapshot, fastcat records which engine filled a Redis db and refuses to load the
other on top:

```python
>>> f = fastcat.FastCat(language='et', engine='databus')
>>> f.load()
>>> f.load(engine='wiki-archive')
RuntimeError: Language 'et' is already loaded in this redis db from the 'databus'
engine, so loading 'wiki-archive' data would merge two different snapshots.
Flush this db first (e.g. FastCat.db.flushdb()) or point this language at another db.
```

To keep both side by side, give the other one a database of its own:

```python
>>> import redis
>>> archive = fastcat.FastCat(db=redis.Redis(db=15), language='et')
>>> archive.load()
>>> sorted(archive.broader("Tallinn"))
['Eesti linnad', 'Hansalinnad', 'Harju maakonna omavalitsused']
>>> sorted(f.broader("Tallinn"))
['Eesti asulate kategooriad', 'Harju maakonna omavalitsusüksuste kategooriad']
```

`wiki-archive` stays the default: it needs no metadata lookup, is unaffected by
the Databus being down, and leaves existing installs on the data they already
have.

You can list the engines from code:

```python
>>> fastcat.FastCat.get_supported_engines()
('wiki-archive', 'databus')
>>> fastcat.FastCat.get_implemented_engines()
('wiki-archive', 'databus')
```

#### How long loading takes

`load()` pipelines its writes to Redis and streams the dump rather than holding
it in memory, so populating a language is quick and cheap:

| Language | Category keys | Load time | Peak memory |
| --- | --- | --- | --- |
| Czech | 151,019 | 4.1s | 55 MB |
| German | 359,819 | 10s | 56 MB |
| English | 1,838,204 | 56s | 58 MB |

(Measured on a laptop with Python 3.13 against a local Redis 7, dump already
downloaded. Before `0.2.4` the same Czech load took 91.5s and English held
1.26 GB in memory.)

`load()` takes a few optional arguments:

| Argument | Default | What it does |
| --- | --- | --- |
| `language` | the object's language | Which language to load. |
| `engine` | the object's engine | Download source for this call only. |
| `batch_size` | `10000` | Redis commands buffered per pipeline flush; the default is a reasonable trade between speed and memory. |
| `progress_bar` | `True` | Draw a progress bar while loading. |
| `verbose` | `False` | Print what is happening; `2` and up print every relation. |

Downloaded dumps are cached inside the installed package, as
`fastcat/data/skos-<engine>-<language>.nt.bz2`, and the language → Redis db
mapping is pickled next to them in `fastcat/settings/`. Delete a dump to force
a fresh download.

A download only takes that name once it is complete, so an interrupted one
(Ctrl-C, a dropped connection, 60 seconds without data) leaves nothing behind,
and the next `load()` starts it again. If a cached dump turns out to be damaged
while loading, fastcat deletes it and raises `DamagedDumpError`, a
`RuntimeError`; run `load()` again to download it afresh.

Development
-----------

See [CONTRIBUTING.md](https://github.com/oskar-j/fastcat/blob/master/CONTRIBUTING.md)
for the guidelines and the release process.

With [uv](https://docs.astral.sh/uv/), which installs the exact versions from
the committed `uv.lock`:

```
$ uv sync
$ uv run pytest
```

Or with pip:

```
$ pip install -e '.[dev]'
$ pytest
```

That runs the fast, offline tests. The end-to-end tests need a Redis server and
download a SKOS dump per language from DBpedia, so they are opt-in:

```
$ docker compose up -d redis      # or your own local Redis
$ pytest --run-integration
```

The compose file also defines a `fastcat` container with the package and its
dev dependencies installed, for running the suite in a clean environment:

```
$ docker compose run --rm fastcat pytest
```

Q&A
---

#### How well is it tested?

The offline unit tests run on every push and pull request, on Python `3.10`
through `3.14`. The integration tests load a real dump for each of the nine
languages and check a known broader/narrower pair in each
([`tests/language_cases.py`](https://github.com/oskar-j/fastcat/blob/master/tests/language_cases.py)).
Feedback is still very welcome under [ticket #7](https://github.com/oskar-j/fastcat/issues/7).

#### What are the biggest drawbacks of fastcat?

DBpedia SKOS files move around, and that has already bitten this project once:
the rolling `current` tree fastcat downloaded from was withdrawn, and
*downloading Wikipedia data* stopped working entirely until `0.2.3` repointed
it at the archived 2016-10 release. Pinning to an archive buys stable URLs at
the cost of **data that stops in 2016**, so pass `engine='databus'` for current
categories.

Each language takes one of Redis's numbered databases, of which there are 16
by default, so that is also the cap on languages. Last but not least, each
language means a one-off download of up to ~45 MB.

#### Which Python versions are supported?

Python `3.10` and above (tested on GitHub Actions against `3.10` through `3.14`).
Releases up to `0.1.2` supported Python `3.5`+; if you are stuck on an older
interpreter, pin `fastcat==0.1.2`.

#### Which languages are supported?

The nine in the [table above](#currently-supported-languages-and-their-codes).
From code, `FastCat.get_supported_languages()` returns their names:

```python
>>> fastcat.FastCat.get_supported_languages()
dict_keys(['Czech', 'English', 'Estonian', 'German', 'Japanese', 'Polish', 'Portuguese', 'Russian', 'Ukrainian'])
```

Adding one takes an entry in `src/fastcat/lang.py`, a category-prefix pattern
in `src/fastcat/interface.py` and a known relation in `tests/language_cases.py`.
If your language is missing, an [issue](https://github.com/oskar-j/fastcat/issues)
or a pull request is very welcome.

#### What's coming next?

Support for the rest of the European languages. Exporting an n-level tree of
categories to a CSV or GraphML file. Moving the downloaded dumps and the
language mapping out of the package directory into a proper user cache
directory.

License
-------

[Creative Commons Attribution-ShareAlike 3.0](https://creativecommons.org/licenses/by-sa/3.0/)

### Attribution

This software is a fork of the [fastcat](https://github.com/edsu/fastcat) tool
created by [Ed Summers](https://github.com/edsu). Changes were made under the
*Creative Commons Attribution-ShareAlike 3.0* license and are described in
commit messages. The major ones are porting the code to Python 3 and adding
support for more than one language.
