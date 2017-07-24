#!/usr/bin/env python

import os
import re
import bz2
from fastcat.utils import normalize_language
from urllib import request, parse
import redis
import fastcat.lang as languages


skos_file_pattern = "data/skos-%lang%.nt.bz2"
ntriple_pattern = re.compile('^<(.+)> <(.+)> <(.+)> \.\n$')
ntriple_pattern_wide = re.compile('^<(.+)> <(.+)> <(.+)> <(.+)> \.\n$')


class FastCat(object):

    def __init__(self, db=None, language=None):
        # Load most recent language-redis mapping
        languages.load_settings()

        # Initialize redis client object
        if db is None:

            if language is None:

                # Check if language-redis mapping is ok
                assert languages.languages.keys().__contains__('en')

                # Initialize connection for English dataset
                db = redis.Redis()  # default is db=0
            else:

                # Intialize connection for any other language dataset
                normalized_language = normalize_language(language)

                try:
                    db = redis.Redis(db=languages.get_slot(normalized_language))
                except ValueError:
                    db = redis.Redis(db=languages.save_settings(normalized_language))

        # There must be always only one redis client
        self.db = db

    def switch_language(self, language):
        """Switch language on an existing fastcat object"""
        try:

            slot = languages.get_slot(language)
            self.db = redis.Redis(db=slot)
        except ValueError:

            slot = languages.save_settings(language)
            self.db = redis.Redis(db=slot)
            self.load(language)

    def get_current_language(self):
        """Get current language"""
        return languages.get_language(slot=self.db.connection_pool.connection_kwargs['db'])

    def broader(self, cat):
        """Pass in a Wikipedia category and get back a list of broader Wikipedia
        categories.
        """
        return list(self.db.smembers("b:%s" % cat))

    def narrower(self, cat):
        """Pass in a Wikipedia category and get back a list of narrower Wikipedia
        categories.
        """
        return list(self.db.smembers("n:%s" % cat))

    def load(self, language=None, verbose=False):
        """Fill Redis with Wikipedia SKOS data"""
        if language is None:
            language = self.get_current_language()

        if self.db.get("loaded-skos"):
            if verbose:
                print('Wikipedia SKOS for {} language is already loaded to Redis!'.format(language))
            return

        skos_file = skos_file_pattern.replace('%lang%', language)

        if not os.path.isfile(skos_file):
            if verbose:
                print('Downloading SKOS .gzip file for langauge: {}'.format(language))
            self._download(language, verbose)

        if verbose:
            print("Loading {} file".format(skos_file))

        uncompressed = bz2.BZ2File(skos_file).readlines()

        for line in uncompressed:

            if language == 'en':
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

            if verbose > 1:
                print('Narrower: {}, broader: {}'.format(narrower, broader))

            self.db.sadd("b:%s" % narrower, broader)
            self.db.sadd("n:%s" % broader, narrower)

            if verbose > 1:
                print("Added %s -> %s" % (broader, narrower))

        self.db.set("loaded-skos", "1")

    def _download(self, language, verbose):
        if verbose:
            print("Downloading Wikipedia SKOS file from DBpedia")

        normalized_language = normalize_language(language)

        if normalized_language == 'en':
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
        if language == 'en':
            m = re.search("^http://dbpedia.org/resource/Category:(.+)$", url_pattern)
        elif language == 'pt':
            m = re.search("^http://pt.dbpedia.org/resource/Categoria:(.+)$", url_pattern)
        else:
            raise NotImplementedError
        return parse.unquote(m.group(1).replace("_", " "))
