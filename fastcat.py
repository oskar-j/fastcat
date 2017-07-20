#!/usr/bin/env python

import os
import re
import bz2
import urllib
from urllib import request, parse
import redis
from lang import languages

skos_file = "skos.nt.bz2"
ntriple_pattern = re.compile('^<(.+)> <(.+)> <(.+)> \.\n$')


class FastCat(object):

    def __init__(self, db=None):
        if db == None:
            db = redis.Redis()
        self.db = db

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

    def load(self, language='en', verbose=False):
        if self.db.get("loaded-skos"):
            return 

        if not os.path.isfile(skos_file):
            self.download(language, verbose)

        if verbose:
            print("Loading {} file".format(skos_file))

        uncompressed = bz2.BZ2File(skos_file).readlines()

        for line in uncompressed:
            m = ntriple_pattern.match(line.decode('utf-8'))
            
            if not m: 
                continue

            s, p, o = m.groups()
            if p != "http://www.w3.org/2004/02/skos/core#broader":
                continue

            narrower = self._name(s)
            broader = self._name(o)
            self.db.sadd("b:%s" % narrower, broader)
            self.db.sadd("n:%s" % broader, narrower)

            if verbose > 1:
                print("Added %s -> %s" % (broader, narrower))

        self.db.set("loaded-skos", "1")

    def download(self, language, verbose):
        if verbose:
            print("Downloading Wikipedia SKOS file from DBpedia")

        language_normalized = language.lower().replace('_', '-')

        if language in ['en', 'en-uk', 'en-us', 'us-us', 'uk-uk']:
            url = 'http://downloads.dbpedia.org/current/core/skos_categories_en.ttl.bz2'
        else:
            url = 'http://downloads.dbpedia.org/current/core-i18n/{}/skos_categories_{}.tql.bz2'.format(
                language_normalized, language_normalized)

        request.urlretrieve(url, filename=skos_file)

        if verbose:
            print("Finished downloading {} file".format(skos_file))

    def _name(self, url_pattern):
        m = re.search("^http://dbpedia.org/resource/Category:(.+)$", url_pattern)
        return parse.unquote(m.group(1).replace("_", " "))
