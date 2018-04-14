fastcat
=======

Fastcat is a little Python library for quickly looking up broader/narrower 
relations in Wikipedia categories locally. The idea is that fastcat can be
useful in situations where you need to rapidly lookup category relations,
but don't want to hammer on the [Wikipedia
API](http://en.wikipedia.org/w/api.php). Fastcat relies on Redis and the 
[SKOS file](http://downloads.dbpedia.org/current/en/skos_categories_en.nt.bz2) that DBpedia makes available basing on the Wikipedia [MySQL dumps](http://dumps.wikimedia.org/enwiki/latest/).

![fastcat logo](http://datageek.pl/github/fastcat_logo-small.png)

Attribution
-----

This software is a fork of [fastcat](https://github.com/edsu/fastcat) tool created by [Ed Summers](https://github.com/edsu). Some changes were made under the *Creative Commons Attribution-ShareAlike 3.0* license, and they are described in commit messages.
 
Usage
-----

The first time you import fastcat you'll need to populate your Redis database
with the category data from DBpedia. To do that instantiate a FastCat object
and call the `load` method. After that you can use it to do lookups.

```python
>>> import fastcat
>>> f = fastcat.FastCat()
>>> f.load()
...
>>> print fastcat.broader("Computer programming")
['Software engineering', 'Computing']
>>> print fastcat.narrower("Computer programming")
['Programming idioms', 'Programming languages', 'Concurrent computing', 'Source code', 'Refactoring', 'Data structures', 'Programming games', 'Computer programmers', 'Version control', 'Anti-patterns', 'Programming constructs', 'Algorithms', 'Web Services tools', 'Programming paradigms', 'Software optimization', 'Debugging', 'Computer programming tools', 'Computer libraries', 'Programming contests', 'Archive networks', 'Self-hosting software', 'Educational abstract machines', 'Software design patterns', 'Computer arithmetic']
```

Install
-------

### Redis installation

You first need to setup Redis server on your machine as follows.

On Mac:

```
$ brew install redis
```

On Linux:

```
$ sudo apt-get install redis-server
```

On Windows:

> Please refer to instruction on installing [Vagrant Redis](https://github.com/ServiceStack/redis-windows)

### Installing module

If you are ready, installing Fastcat is pretty straightforward:

```
$ pip install git+https://github.com/takuti/fastcat.git
```

Usage
-------

1. ./load.py
1. brew a pot of coffee while the data is downloaded and loaded into redis
1. profit?

License
-------

[Creative Commons Attribution-ShareAlike 3.0](http://creativecommons.org/licenses/by-sa/3.0/)
