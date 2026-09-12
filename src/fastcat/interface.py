#!/usr/bin/env python

import os
import sys
import re
import bz2
import hashlib
from fastcat.utils import normalize_language, print_progress_bar, get_wikipedia_mapping
from urllib import error, request, parse
import redis
import fastcat.store as store
import fastcat.lang as languages
import fastcat.engines as engines
from fastcat.engines import DEFAULT_ENGINE, skos_source, validate_engine


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

# The engine is part of the name so dumps of the same language from different
# sources cannot overwrite each other.
skos_file_pattern = os.path.join(
    os.path.dirname(os.path.realpath(p)), 'data', 'skos-%engine%-%lang%.nt.bz2')


def skos_file_for(language, engine=DEFAULT_ENGINE):
    """Local path fastcat caches a language's dump at."""
    return skos_file_pattern.replace('%lang%', language).replace('%engine%', engine)

# Where to look for Redis unless the caller says otherwise. The environment
# variables make a containerised Redis (see docker-compose.yml) usable without
# passing connection arguments around.
DEFAULT_REDIS_HOST = os.environ.get('FASTCAT_REDIS_HOST', 'localhost')
DEFAULT_REDIS_PORT = int(os.environ.get('FASTCAT_REDIS_PORT', 6379))

#: Redis commands buffered before a pipeline is flushed. Without batching each
#: triple costs two full round-trips, which dominates the load time.
DEFAULT_BATCH_SIZE = 10000

ntriple_pattern = re.compile(r'^<(.+)> <(.+)> <(.+)> \.\n$')
ntriple_pattern_wide = re.compile(r'^<(.+)> <(.+)> <(.+)> <(.+)> \.\n$')


class FastCatBase(object):

    def _download(self, language, verbose, engine=DEFAULT_ENGINE):
        if verbose:
            print("Downloading Wikipedia SKOS file from DBpedia")

        normalized_language = normalize_language(language)
        wikipedia_mapping = get_wikipedia_mapping(normalized_language)

        source = skos_source(wikipedia_mapping, engine)
        skos_file = skos_file_for(normalized_language, engine)

        if verbose:
            print('-- request.urlretrieve for file {}'.format(skos_file))

        try:
            request.urlretrieve(source.url, filename=skos_file)
        except error.HTTPError as http_error:
            # Leaving a truncated file behind would make the next load() skip
            # the download and fail while parsing instead.
            self._discard(skos_file)

            raise RuntimeError(
                'Could not download the SKOS dump for language {!r} from {} '
                '({}). The {!r} engine may no longer serve this file.'.format(
                    normalized_language, source.url, http_error, engine)) from http_error

        # The Databus publishes a checksum per file; the wiki archive does not.
        if source.sha256:
            digest = self._sha256(skos_file)

            if digest != source.sha256:
                self._discard(skos_file)

                raise RuntimeError(
                    'Checksum mismatch for the {!r} dump downloaded from {}: '
                    'expected {}, got {}. The file has been discarded.'.format(
                        normalized_language, source.url, source.sha256, digest))

            if verbose:
                print('Checksum verified ({})'.format(digest[:16]))

        if verbose:
            print("Finished downloading {} file".format(skos_file))

    @staticmethod
    def _discard(path):
        if os.path.isfile(path):
            os.remove(path)

    @staticmethod
    def _sha256(path, chunk_size=1024 * 1024):
        digest = hashlib.sha256()

        with open(path, 'rb') as handle:
            for chunk in iter(lambda: handle.read(chunk_size), b''):
                digest.update(chunk)

        return digest.hexdigest()

    def _name(self, url_pattern, language):
        if language == languages.available_languages['English'].id:
            m = re.search("^http://dbpedia.org/resource/Category:(.+)$", url_pattern)
        elif language == languages.available_languages['Czech'].id:
            m = re.search("^http://cs.dbpedia.org/resource/Kategorie:(.+)$", url_pattern)
        elif language == languages.available_languages['Estonian'].id:
            m = re.search("^http://et.dbpedia.org/resource/Kategooria:(.+)$", url_pattern)
        elif language == languages.available_languages['German'].id:
            m = re.search("^http://de.dbpedia.org/resource/Kategorie:(.+)$", url_pattern)
        elif language == languages.available_languages['Japanese'].id:
            m = re.search("^http://ja.dbpedia.org/resource/Category:(.+)$", url_pattern)
        elif language == languages.available_languages['Polish'].id:
            m = re.search("^http://pl.dbpedia.org/resource/Kategoria:(.+)$", url_pattern)
        elif language == languages.available_languages['Portuguese'].id:
            m = re.search("^http://pt.dbpedia.org/resource/Categoria:(.+)$", url_pattern)
        elif language == languages.available_languages['Russian'].id:
            m = re.search("^http://ru.dbpedia.org/resource/Категория:(.+)$", url_pattern)
        elif language == languages.available_languages['Ukrainian'].id:
            m = re.search("^http://uk.dbpedia.org/resource/Категорія:(.+)$", url_pattern)
        else:
            raise NotImplementedError
        return parse.unquote(m.group(1).replace("_", " "))


class FastCat(FastCatBase):

    def __init__(self, db=None, language=None, engine=DEFAULT_ENGINE, **kwargs):
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
            engine (:obj:`str`, optional): Where dumps are downloaded from. Defaults to
                ``'wiki-archive'``. See :mod:`fastcat.engines`.
            kwargs (:obj:`dict`, optional): Any arguments, which you wish to pass to the Redis client.

        Raises:
            ValueError: The engine name is not recognised.
            NotImplementedError: The engine is known but not implemented yet, as
                ``'databus'`` currently is.

        """

        super(FastCatBase, self).__init__()

        # Fail before touching redis if the caller asked for an engine that
        # cannot download anything
        validate_engine(engine)
        self.engine = engine

        # Load most recent language-redis mapping
        store.load_settings()

        # Anything not set here is left at the redis client's own default
        options = {'host': DEFAULT_REDIS_HOST, 'port': DEFAULT_REDIS_PORT}
        options.update(kwargs)

        # Remembered so that every later connection (a different language means
        # a different redis db) reaches the same server
        self._options = options

        # Initialize redis client object
        if db is None:

            if language is None:

                # Check if language-redis mapping is ok
                assert 'en' in store.languages

                # Initialize connection for English dataset
                db = redis.Redis(**options)  # default is db=0
            else:

                # Initialize connection for any other language dataset
                normalized_language = normalize_language(language)

                try:
                    slot = store.get_slot(normalized_language)
                except ValueError:
                    slot = store.save_settings(normalized_language)

                db = redis.Redis(db=slot, **options)

        # There must be always only one redis client
        self.db = db

    def switch_language(self, language):
        """Switch language on an existing FastCat object."""
        try:

            slot = store.get_slot(language)
            self.db = redis.Redis(db=slot, **self._options)
        except ValueError:

            slot = store.save_settings(language)
            self.db = redis.Redis(db=slot, **self._options)
            self.load(language)

    def get_current_language(self):
        """Get current language."""
        return store.get_language(slot=self.db.connection_pool.connection_kwargs['db'])

    @staticmethod
    def get_supported_languages():
        """Get list of supported languages."""
        return languages.available_languages.keys()

    @staticmethod
    def get_supported_engines():
        """Get every known download engine, implemented or not.

        See :func:`get_implemented_engines` for the ones that work today.
        """
        return engines.available_engines

    @staticmethod
    def get_implemented_engines():
        """Get the download engines that can actually fetch a dump."""
        return engines.implemented_engines

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

    def _loaded_engine(self):
        """Which engine's data populates this redis db, or None if it is empty.

        Data written before 0.3.0 carries no engine marker; the wiki archive
        was the only source then, so that is what it is taken to be.
        """
        if not self.db.get("loaded-skos"):
            return None

        recorded = self.db.get("loaded-engine")

        if recorded is None:
            return engines.WIKI_ARCHIVE

        return recorded.decode('utf-8') if isinstance(recorded, bytes) else recorded

    def load(self, language=None, verbose=False, progress_bar=True, engine=None,
             batch_size=DEFAULT_BATCH_SIZE):
        """Fill Redis with Wikipedia SKOS data.

        Args:
            language (:obj:`str`, optional): Language to load. Defaults to the
                language this object is connected to.
            verbose (:obj:`bool` or :obj:`int`, optional): Higher values print more.
            progress_bar (:obj:`bool`, optional): Draw a progress bar while loading.
            engine (:obj:`str`, optional): Override the object's download engine
                for this call. See :mod:`fastcat.engines`.
            batch_size (:obj:`int`, optional): How many Redis commands to buffer
                before flushing the pipeline. Lower it to cap memory, raise it
                for a little more speed.

        Raises:
            ValueError: ``batch_size`` is smaller than 1.
        """
        if batch_size < 1:
            raise ValueError(
                'batch_size must be at least 1, got {!r}'.format(batch_size))

        if language is None:
            language = self.get_current_language().alpha_2.lower()

        if engine is None:
            engine = self.engine
        validate_engine(engine)

        loaded_engine = self._loaded_engine()

        if loaded_engine is not None:
            if loaded_engine != engine:
                # The engines publish different snapshots of Wikipedia. Writing
                # one on top of the other would merge them into a single set of
                # relations belonging to neither.
                raise RuntimeError(
                    'Language {!r} is already loaded in this redis db from the '
                    '{!r} engine, so loading {!r} data would merge two '
                    'different snapshots. Flush this db first (e.g. '
                    'FastCat.db.flushdb()) or point this language at another '
                    'db.'.format(language, loaded_engine, engine))

            if verbose:
                self._is_loaded(language, verbose)

            print('Loading aborted (language already exists)')
            return

        skos_file = skos_file_for(language, engine)

        if not os.path.isfile(skos_file):
            if verbose:
                print('Downloading SKOS .gzip file for langauge: {}'.format(language))
            self._download(language, verbose, engine)

        if verbose:
            print("Loading {} file".format(skos_file))

        if verbose:
            print('Unpacking DBpedia .GZ file... this may take some time.')

        if verbose:
            print('Starting process of adding DBpedia data to Redis instance')

        # Buffer the writes: one SADD per triple means a round-trip to Redis
        # per triple, and there are millions of them.
        pipe = self.db.pipeline(transaction=False)
        pending = 0

        # Progress is tracked in *compressed* bytes consumed. Counting lines up
        # front would mean decompressing the whole dump into memory first,
        # which is what the previous implementation did.
        # The fallback keeps an empty file from dividing by zero
        total_bytes = os.path.getsize(skos_file) or 1
        last_tick = -1

        with open(skos_file, 'rb') as raw, bz2.BZ2File(raw) as uncompressed:

            for line in uncompressed:

                if progress_bar:
                    # Redrawing on every line puts terminal I/O on the hot
                    # path, so only redraw when the bar would actually change.
                    consumed = min(raw.tell(), total_bytes)
                    tick = consumed * 1000 // total_bytes
                    if tick != last_tick:
                        print_progress_bar(consumed, total_bytes, prefix='Progress:',
                                           suffix='Complete', length=50)
                        last_tick = tick

                text = line.decode('utf-8')

                if text.startswith('#'):
                    # Dumps open with a "# started ..." header line
                    continue

                # Archived dumps are plain n-triples for every language, but the
                # quad (.tql) flavour of the same data is still out there, so both
                # shapes are accepted.
                m = ntriple_pattern.match(text) or ntriple_pattern_wide.match(text)

                if not m:
                    if verbose > 2:
                        print('ntripple pattern failed to match')
                    continue

                groups = m.groups()

                if len(groups) == 4:
                    s, p, o, meta = groups
                elif len(groups) == 3:
                    s, p, o = groups
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

                    pipe.sadd("b:%s" % narrower, broader)
                    pipe.sadd("n:%s" % broader, narrower)
                    pending += 2

                except UnicodeEncodeError as uee:

                    print('Narrower: {}, broader: {}'.format(narrower.encode("utf-8"), broader.encode("utf-8")))
                    raise uee

                if pending >= batch_size:
                    pipe.execute()
                    pending = 0

                if verbose > 1:
                    print("Added %s -> %s" % (broader, narrower))

        if pending:
            pipe.execute()

        if progress_bar:
            print_progress_bar(total_bytes, total_bytes, prefix='Progress:',
                               suffix='Complete', length=50)

        # Only once every triple is in, so an interrupted load is not mistaken
        # for a complete one
        self.db.set("loaded-skos", "1")
        self.db.set("loaded-engine", engine)
