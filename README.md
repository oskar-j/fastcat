fastcat
=======

[![Build Status](https://travis-ci.org/oskar-j/fastcat.svg?branch=master)](https://travis-ci.org/oskar-j/fastcat)
[![Ebert](https://ebertapp.io/github/oskar-j/fastcat.svg)](https://ebertapp.io/github/oskar-j/fastcat)

Fastcat is a little Python library for quickly looking up broader/narrower 
relations in Wikipedia categories locally. The idea is that fastcat can be
useful in situations where you need to rapidly lookup category relations,
but don't want to hammer on the [Wikipedia
API](http://en.wikipedia.org/w/api.php). Fastcat relies on Redis and the 
[SKOS file](http://downloads.dbpedia.org/current/en/skos_categories_en.nt.bz2) that DBpedia makes available basing on the Wikipedia [MySQL dumps](http://dumps.wikimedia.org/enwiki/latest/).

![fastcat logo](http://datageek.pl/github/fastcat_logo-small.png)

Attribution
-----

This software is a fork of [fastcat](https://github.com/edsu/fastcat) tool created by [Ed Summers](https://github.com/edsu). Some changes were made under the *Creative Commons Attribution-ShareAlike 3.0* license, and they are described in commit messages. Major changes are porting the code to Python 3 as well as adding support for more languages.
 
Usage
-----

The first time you import fastcat you'll need to populate your Redis database
with the category data from DBpedia. To do that instantiate a FastCat object
and call the `load` method. After that you can use it to do lookups.

```python
>>> import fastcat
>>> f = fastcat.FastCat()
>>> f.load()  # brew a pot of coffee while the data is downloaded and loaded into redis
...
>>> print(f.broader("Computer programming"))
['Software engineering', 'Computing']
>>> print(f.narrower("Computer programming"))
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

Please refer to instruction on installing [Vagrant Redis](https://github.com/ServiceStack/redis-windows). You will
need an Ubuntu installation on your Windows, more information can be found here: [Install your Linux Distribution of Choice](https://docs.microsoft.com/pl-pl/windows/wsl/install-win10)

### Installing the module

If you are ready, installing Fastcat is pretty straightforward:

```
$ pip install git+https://github.com/oskar-j/fastcat.git
```

Q&A
-------

#### How much is is tested?

It's still in early stage of development, please share some feedback with me

#### What are biggest drawbacks of Fastcat?

DBpedia SKOS file is prone to constant change, which means: a) *loading data* in fastcat can stop working in some distant future, b) it takes around 40 MB of your transfer (size depends on selected language)

#### Which Python versions are supported?

Basically all Python 3+ versions. According to Travis, it works with PyPy as well.

#### Which languages are supported?

Currently only English and Portuguese languages are tested. You can try to add more SKOS languages, but they're not guaranteed to work due to possible differences in the file structure

#### What's coming next?

Support of Japanese language as well as adding Fastcat to public python repository. Exporting n-size tree of categories to CSV or GraphML file. 

License
-------

[Creative Commons Attribution-ShareAlike 3.0](http://creativecommons.org/licenses/by-sa/3.0/)
