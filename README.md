fastcat
=======

fastcat is a little Python library for quickly looking up broader/narrower 
relations in Wikipedia categories locally. The idea is that fastcat can be
useful in situations where you need to rapidly lookup category relations,
but don't want to hammer on the [Wikipedia
API](http://en.wikipedia.org/w/api.php). fastcat relies on redis, and a 
[SKOS](http://downloads.dbpedia.org/current/en/skos_categories_en.nt.bz2) 
file that dbpedia make available based on the Wikipedia MySQL
[dumps](http://dumps.wikimedia.org/enwiki/latest/).

Attribution
-----

This software is a fork of [fastcat](https://github.com/edsu/fastcat) tool created by [Ed Summers](https://github.com/edsu). Some changes were made under the *Creative Commons Attribution-ShareAlike 3.0* license, and they are described in commit messages.
 
Usage
-----

The first time you import fastcat you'll need to populate your redis database
with the category data from dbpedia. To do that instantiate a FastCat object
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

To install and load fastcat on Ubuntu try this:

1. apt-get install redis-server virtualenvwrapper git-core
1. git clone git://github.com/edsu/fastcat.git
1. cd fastcat
1. mkvirtualenv fastcat
1. pip install -r requirements.pip
1. ./load.py
1. brew a pot of coffee while the data is downloaded and loaded into redis
1. profit?

License
-------

[Creative Commons Attribution-ShareAlike 3.0](http://creativecommons.org/licenses/by-sa/3.0/)
