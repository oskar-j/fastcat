#!/usr/bin/env python

import os
import sys
import re
import bz2
from fastcat.utils import normalize_language, print_progress_bar
from urllib import request, parse
import redis
import fastcat.store as store
import fastcat.lang as languages


try:
    p = __file__
except NameError:
    p = sys.argv[0]


data_location = os.path.join(os.path.dirname(os.path.realpath(p)), 'data')
if not os.path.isdir(data_location):
    os.makedirs(data_location)
settings_location = os.path.join(os.path.dirname(os.path.realpath(p)), 'settings')
if not os.path.isdir(settings_location):
    os.makedirs(settings_location)

skos_file_pattern = os.path.join(os.path.dirname(os.path.realpath(p)), 'data', 'skos-%lang%.nt.bz2')

ntriple_pattern = re.compile('^<(.+)> <(.+)> <(.+)> \.\n$')
ntriple_pattern_wide = re.compile('^<(.+)> <(.+)> <(.+)> <(.+)> \.\n$')


class FastCatBase(object):

    def _download(self, language, verbose):
        if verbose:
            print("Downloading Wikipedia SKOS file from DBpedia")

        normalized_language = normalize_language(language)

        if normalized_language == languages.available_languages['English'].id:
            url = 'http://downloads.dbpedia.org/current/core/skos_categories_en.ttl.bz2'
        else:
            url = 'http://downloads.dbpedia.org/current/core-i18n/{}/skos_categories_{}.tql.bz2'.format(
                normalized_language, normalized_language)

        skos_file = skos_file_pattern.replace('%lang%', normalized_language)

        if verbose:
            print('-- request.urlretrieve for file {}'.format(skos_file))

        request.urlretrieve(url, filename=skos_file)

        if verbose:
            print("Finished downloading {} file".format(skos_file))

    def _name(self, url_pattern, language):
        if language == languages.available_languages['English'].id:
            m = re.search("^http://dbpedia.org/resource/Category:(.+)$", url_pattern)
        elif language == languages.available_languages['German'].id:
            m = re.search("^http://de.dbpedia.org/resource/Kategorie:(.+)$", url_pattern)
        elif language == languages.available_languages['Japanese'].id:
            m = re.search("^http://ja.dbpedia.org/resource/Category:(.+)$", url_pattern)
        elif language == languages.available_languages['Polish'].id:
            m = re.search("^http://pl.dbpedia.org/resource/Kategoria:(.+)$", url_pattern)
        elif language == languages.available_languages['Portuguese'].id:
            m = re.search("^http://pt.dbpedia.org/resource/Categoria:(.+)$", url_pattern)
        else:
            raise NotImplementedError
        return parse.unquote(m.group(1).replace("_", " "))


class FastCat(FastCatBase):

    def __init__(self, db=None, language=None, **kwargs):
        """Creates a new FastCast object, an interface to Wikipedia categories.

        The __init__ method creates the FastCat object, which acts as the main and only
        interface in communicating with the Redis server (where the Wikipedia categories are
        first loaded (stored) and then retrieved on demand). Default settings mean that you're connecting
        to a Redis instance on the localhost and 6379 port, and your current language of categories is English.
        It's possible to pass your own Redis client object into the 'db' arg, or,
        alternatively, custom args to the Redis client __init__ method.

        Note:
            No need to pass any extra arguments if you don't understand what you're doing

        Args:
            db (:obj:`Redis`, optional): Custom Redis client.
            language (:obj:`str`, optional): Choose the default language.
            kwargs (:obj:`dict`, optional): Any arguments, which you wish to pass to the Redis client.

        """

        super(FastCatBase, self).__init__()
        # Load most recent language-redis mapping
        store.load_settings()

        options = {
            'host': 'localhost', 'port': 6379,
                 'password': None, 'socket_timeout': None,
                 'socket_connect_timeout': None,
                 'socket_keepalive': None, 'socket_keepalive_options': None,
                 'connection_pool': None, 'unix_socket_path': None,
                 'encoding': 'utf-8', 'encoding_errors': 'strict',
                 'charset': None, 'errors': None,
                 'decode_responses': False, 'retry_on_timeout': False,
                 'ssl': False, 'ssl_keyfile': None, 'ssl_certfile': None,
                 'ssl_cert_reqs': None, 'ssl_ca_certs': None,
                 'max_connections': None }

        options.update(kwargs)

        # Initialize redis client object
        if db is None:

            if language is None:

                # Check if language-redis mapping is ok
                assert store.languages.keys().__contains__('en')

                # Initialize connection for English dataset
                db = redis.Redis(**options)  # default is db=0
            else:

                # Initialize connection for any other language dataset
                normalized_language = normalize_language(language)

                try:
                    db = redis.Redis(db=store.get_slot(normalized_language))
                except ValueError:
                    db = redis.Redis(db=store.save_settings(normalized_language))

        # There must be always only one redis client
        self.db = db

    def switch_language(self, language):
        """Switch language on an existing FastCat object."""
        try:

            slot = store.get_slot(language)
            self.db = redis.Redis(db=slot)
        except ValueError:

            slot = store.save_settings(language)
            self.db = redis.Redis(db=slot)
            self.load(language)

    def get_current_language(self):
        """Get current language."""
        return store.get_language(slot=self.db.connection_pool.connection_kwargs['db'])

    @staticmethod
    def get_supported_languages():
        """Get list of supported languages."""
        return languages.available_languages.keys()

    def broader(self, cat):
        """Pass in a Wikipedia category and get back a list of broader Wikipedia categories."""
        return [s.decode('utf-8') for s in self.db.smembers("b:%s" % cat)]

    def narrower(self, cat):
        """Pass in a Wikipedia category and get back a list of narrower Wikipedia categories."""
        return [s.decode('utf-8') for s in self.db.smembers("n:%s" % cat)]

    def _is_loaded(self, language, verbose=False):
        # TODO: process depending on language
        if self.db.get("loaded-skos"):
            if verbose:
                print('Wikipedia SKOS for {} language is already loaded to Redis!'.format(language))
            return True
        else:
            return False

    def load(self, language=None, verbose=False, progress_bar=True):
        """Fill Redis with Wikipedia SKOS data."""
        if language is None:
            language = self.get_current_language().alpha_2

        if self._is_loaded(language, verbose):
            print('Loading aborted (language already exists)')
            return

        skos_file = skos_file_pattern.replace('%lang%', language)

        if not os.path.isfile(skos_file):
            if verbose:
                print('Downloading SKOS .gzip file for langauge: {}'.format(language))
            self._download(language, verbose)

        if verbose:
            print("Loading {} file".format(skos_file))

        if verbose:
            print('Unpacking DBpedia .GZ file... this may take some time.')
        uncompressed = bz2.BZ2File(skos_file).readlines()
        l = len(uncompressed)

        if verbose:
            print('Starting process of adding DBpedia data to Redis instance')

        for i, line in enumerate(uncompressed):

            if progress_bar:
                print_progress_bar(i, l, prefix='Progress:', suffix='Complete', length=50)

            if language == languages.available_languages['English'].id:
                m = ntriple_pattern.match(line.decode('utf-8'))
            else:
                # Non-english (i18l) SKOS files have different format
                m = ntriple_pattern_wide.match(line.decode('utf-8'))

            if not m:
                if verbose > 2:
                    print('ntripple pattern failed to match')
                continue

            groups = m.groups()

            if len(groups) == 4:
                s, p, o, meta = m.groups()
            elif len(groups) == 3:
                s, p, o = m.groups()
            else:
                raise ValueError

            if p != "http://www.w3.org/2004/02/skos/core#broader":
                if verbose > 2:
                    print('p group is not "broader" - {}'.format(p))
                continue

            narrower = self._name(s, language)
            broader = self._name(o, language)

            try:

                if verbose > 1:
                    print('Narrower: {}, broader: {}'.format(narrower, broader))

                self.db.sadd("b:%s" % narrower, broader)
                self.db.sadd("n:%s" % broader, narrower)

            except UnicodeEncodeError as uee:

                print('Narrower: {}, broader: {}'.format(narrower.encode("utf-8"), broader.encode("utf-8")))
                raise uee

            if verbose > 1:
                print("Added %s -> %s" % (broader, narrower))

        self.db.set("loaded-skos", "1")
