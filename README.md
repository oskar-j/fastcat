fastcat
=======

[![Tests](https://github.com/oskar-j/fastcat/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/oskar-j/fastcat/actions/workflows/tests.yml)
[![Publish](https://github.com/oskar-j/fastcat/actions/workflows/publish.yml/badge.svg?branch=master)](https://github.com/oskar-j/fastcat/actions/workflows/publish.yml)
[![PyPI](https://img.shields.io/pypi/v/fastcat)](https://pypi.org/project/fastcat/)
[![Python Versions](https://img.shields.io/pypi/pyversions/fastcat)](https://pypi.org/project/fastcat/)
[![Downloads](https://static.pepy.tech/badge/fastcat)](https://pepy.tech/project/fastcat)
[![License](https://img.shields.io/badge/license-CC%20BY--SA%203.0-blue)](http://creativecommons.org/licenses/by-sa/3.0/)
[![Pending Pull-Requests](https://img.shields.io/github/issues-pr/oskar-j/fastcat)](https://github.com/oskar-j/fastcat/pulls)
[![Github Issues](https://img.shields.io/github/issues/oskar-j/fastcat)](https://github.com/oskar-j/fastcat/issues)
[![Commits Since Release](https://img.shields.io/github/commits-since/oskar-j/fastcat/latest)](https://github.com/oskar-j/fastcat/releases)

Fastcat is a little Python library for quickly looking up broader/narrower 
relations in Wikipedia categories locally. The idea is that fastcat can be
useful in situations where you need to rapidly lookup category relations,
but don't want to hammer on the [Wikipedia
API](http://en.wikipedia.org/w/api.php). Fastcat relies on Redis and the 
[SKOS files](https://downloads.dbpedia.org/2016-10/core-i18n/) that DBpedia makes available basing on 
the Wikipedia [MySQL dumps](http://dumps.wikimedia.org/enwiki/latest/).

![fastcat logo](https://datageek.pl/assets/img/projects/fast_cat.png)

Attribution
-----

This software is a fork of [fastcat](https://github.com/edsu/fastcat) tool created by [Ed Summers](https://github.com/edsu). 
Some changes were made under the *Creative Commons Attribution-ShareAlike 3.0* license, and they are described in commit 
messages. Major changes are porting the code to Python 3 as well as adding support for more than one language.
 
Usage
-----

#### Basic usage 

The first time you import fastcat you'll need to populate your Redis database
with the category data from DBpedia. To do that instantiate a FastCat object
and call the `load` method. After that you can use it to do lookups.

```python
>>> import fastcat
>>> f = fastcat.FastCat()
>>> f.load()  # brew a pot of coffee while the data is downloaded and loaded into redis
...
>>> print(f.broader("Computer programming"))
['Software engineering', 'Software development']
>>> print(f.narrower("Computer programming"))
['Programming languages', 'Algorithms', 'Data structures', 'Computer programming tools', 'Programming games', 'Programming paradigms', 'Anti-patterns', 'Software design patterns', 'Programming constructs', 'Programming contests', 'Concurrent computing', 'Source code', 'Debugging', 'Computer programmers', 'Programming idioms', 'Computer libraries', 'Self-hosting software', 'Programming principles', 'Software optimization', 'Computer programming books', 'Code refactoring', 'Live coding', 'Source code generation', 'Program derivation', 'Visual programming', 'Computer programming folklore']
```

#### Non-english categories

Just fill-in the `language` argument in the `FastCat()` constructor with a language code listed below.

```python
>>> import fastcat
>>> f = fastcat.FastCat(language='de')
>>> f.load()  # brew a pot of coffee while the data is downloaded and loaded into redis
...
>>> print(f.broader("Berlin"))
['Europa nach Ort', 'Deutschland nach Gemeinde', 'Deutschland nach Bundesland']
>>> print(f.narrower("Berlin"))
['Umwelt- und Naturschutz (Berlin)', 'Veranstaltung (Berlin)', 'Stadtplanung (Berlin)', 'Verwaltung (Berlin)', 'Urbaner Freiraum in Berlin als Thema']
```

##### Currently supported languages (and their codes)

1. English (`en`)
2. Estonian (`et`)
3. German (`de`)
4. Japanese (`ja`)
5. Polish (`pl`)
6. Portuguese (`pt`)
7. Russian (`ru`)
8. Ukrainian (`ua`)
9. Czech (`cs`)

#### Where the data comes from

The `engine` argument selects the download source:

```python
>>> import fastcat
>>> f = fastcat.FastCat(engine='wiki-archive')  # the default
>>> f.load()
```

| Engine | Status | What it downloads |
| --- | --- | --- |
| `wiki-archive` | **default** | DBpedia's archived [2016-10 release](https://downloads.dbpedia.org/wiki-archive/dbpedia-version-2016-10.html) |
| `databus` | not implemented yet | DBpedia's current [Databus](https://databus.dbpedia.org/) distribution |

Asking for `databus` raises `NotImplementedError`:

```python
>>> fastcat.FastCat(engine='databus')
NotImplementedError: The 'databus' engine is not implemented yet. Use 'wiki-archive' instead (the default).
```

Note that the archived release is a **snapshot of Wikipedia as it stood in
2016**, so categories added since then are missing. That is the price of stable
URLs: the rolling `current` tree fastcat used before was withdrawn by DBpedia
and every URL under it now returns 404. Fetching today's data is what the
`databus` engine is for.

You can list the engines from code:

```python
>>> fastcat.FastCat.get_supported_engines()
('wiki-archive', 'databus')
>>> fastcat.FastCat.get_implemented_engines()
('wiki-archive',)
```

Install
-------

### Redis installation

You first need to setup Redis server on your machine as follows.

**On Mac:**

```
$ brew install redis
```

**On Linux:**

```
$ sudo apt-get install redis-server
```

**On Windows:**

Please refer to instruction on installing [Vagrant Redis](https://github.com/ServiceStack/redis-windows). You will
need an Ubuntu installation on your Windows, more information can be found 
here: [Install your Linux Distribution of Choice](https://docs.microsoft.com/pl-pl/windows/wsl/install-win10)

**With Docker (any platform):**

If you would rather not install Redis at all, the bundled compose file spins one
up on `localhost:6379`, with the loaded categories kept in a named volume so
they survive a restart:

```
$ docker compose up -d redis
```

The same file also defines a `fastcat` container with the package and its dev
dependencies installed, which is handy for running the suite in a clean
environment:

```
$ docker compose run --rm fastcat pytest
```

Inside a container Redis is not on localhost, so fastcat reads the
`FASTCAT_REDIS_HOST` and `FASTCAT_REDIS_PORT` environment variables (already set
for the `fastcat` service) to find it.

### Installing the module

If you are ready, installing Fastcat is pretty straightforward:

```
$ pip install fastcat
```

Or if you wish to get the newest dev code:

```
$ pip install git+https://github.com/oskar-j/fastcat.git
```

That's it!

### Contributing to the project

#### Guidelines

See [CONTRIBUTING.md](https://github.com/oskar-j/fastcat/blob/master/CONTRIBUTING.md) for more details

#### Running unit tests

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

Q&A
-------

#### How much is is tested?

It's still in early stage of development, please share some feedback with me (under the [ticket #7](https://github.com/oskar-j/fastcat/issues/7)).

#### What are biggest drawbacks of Fastcat?

DBpedia SKOS files move around, and that has already bitten this project once: the rolling `current` tree fastcat
downloaded from was withdrawn, and *downloading Wikipedia data* stopped working entirely until `0.2.3` repointed it at
the archived 2016-10 release. Pinning to an archive buys stable URLs at the cost of **data that stops in 2016** --
until the `databus` engine lands, categories created after that are simply not there. Moreover, due to the
[infrastructure of Redis](http://www.mikeperham.com/2015/09/24/storing-data-with-redis/), you can have a maximum number
of 16 languages (1 slot for a language). Last but not least, it takes around `40 MB` of your web transfer (size depends
on the selected language) to download a single SKOS file.

#### Which Python versions are supported?

Python `3.10` and above (tested on GitHub Actions against `3.10` through `3.14`).
Releases up to `0.1.2` supported Python `3.5`+; if you are stuck on an older
interpreter, pin `fastcat==0.1.2`.

#### Which languages are supported?

There are two ways to check the list of available languages. 

First, is a manual inspection of the [lang.py](https://github.com/oskar-j/fastcat/blob/master/src/fastcat/lang.py) file.

Second way is to call the `get_supported_languages()` method on the `FastCat` object.

#### What's coming next?

Implementing the `databus` engine, so fastcat can pull current categories instead of a 2016 snapshot.
Support for the rest of european languages. Exporting n-size tree of categories to a CSV or GraphML file.
Moving the downloaded dumps and the language mapping out of the package directory into a proper user cache
directory.

License
-------

[Creative Commons Attribution-ShareAlike 3.0](http://creativecommons.org/licenses/by-sa/3.0/)
