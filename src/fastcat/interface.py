#!/usr/bin/env python

import os
import re
import bz2
import hashlib
import http.client
import warnings
from fastcat.utils import (normalize_language, print_progress_bar, get_wikipedia_mapping,
                           resolve_language, supported_language_ids)
from urllib import error, request, parse
import redis
import fastcat.paths as paths
import fastcat.store as store
import fastcat.lang as languages
import fastcat.engines as engines
from fastcat.engines import DEFAULT_ENGINE, skos_source, validate_engine


def skos_file_for(language, engine=DEFAULT_ENGINE):
    """Local path fastcat caches a language's dump at."""
    return os.path.join(paths.data_dir(), _skos_name(language, engine))


def _skos_name(language, engine):
    # The engine is part of the name so dumps of the same language from
    # different sources cannot overwrite each other.
    return 'skos-{}-{}.nt.bz2'.format(engine, language)


# Up to 0.3.5 dumps were cached in data/ inside the package. FastCat() moves
# them to the data directory, once per process.
_legacy_dumps_checked = False


def _adopt_legacy_dumps_once():
    global _legacy_dumps_checked

    if not _legacy_dumps_checked:
        _legacy_dumps_checked = True
        _adopt_legacy_dumps()

        # The old directories go too, unless something is left in them (or
        # the package is read-only)
        paths.remove_quietly(os.path.join(paths.LEGACY_DIR, 'data'))
        paths.remove_quietly(os.path.join(paths.LEGACY_DIR, 'settings'))


def _adopt_legacy_dumps():
    """Move the dumps fastcat 0.3.5 and earlier cached inside the package.

    Each goes to the data directory, unless one of the same name is there
    already, in which case the old one is just removed. On another
    filesystem they are copied instead, and the originals left in place:
    that may be a volume that outlasts the data directory, as with
    docker-compose.yml up to 0.3.5. Other files are left alone.
    """
    legacy = os.path.join(paths.LEGACY_DIR, 'data')

    try:
        present = set(os.listdir(legacy))
    except OSError:
        return

    found = sorted(present & {_skos_name(language, engine)
                              for engine in engines.available_engines
                              for language in supported_language_ids()})

    if not found:
        return

    try:
        target = paths.ensure_data_dir()
    except RuntimeError as exc:
        warnings.warn('{} The dumps that an earlier fastcat cached in {} are '
                      'left there.'.format(exc, legacy), RuntimeWarning, stacklevel=4)
        return

    moving = paths.same_filesystem(legacy, target)
    to_move = [name for name in found if not os.path.exists(os.path.join(target, name))]

    if to_move and moving:
        print('Moving {} cached dump(s) from {} to {}'.format(len(to_move), legacy, target))
    elif to_move:
        print('Copying {} cached dump(s) from {} to {}. {}'.format(
            len(to_move), legacy, target, paths.kept_on_another_filesystem()))

    for name in found:
        source = os.path.join(legacy, name)

        if name not in to_move:
            if moving:
                paths.remove_quietly(source)
            continue

        try:
            (paths.move if moving else paths.copy)(source, os.path.join(target, name))
        except OSError as exc:
            warnings.warn('Could not move {} to {} ({}). It will be downloaded '
                          'again when needed.'.format(source, target, exc),
                          RuntimeWarning, stacklevel=4)


# Where to look for Redis unless the caller says otherwise. The environment
# variables make a containerised Redis (see docker-compose.yml) usable without
# passing connection arguments around.
DEFAULT_REDIS_HOST = os.environ.get('FASTCAT_REDIS_HOST', 'localhost')
DEFAULT_REDIS_PORT = int(os.environ.get('FASTCAT_REDIS_PORT', 6379))

#: Redis commands buffered before a pipeline is flushed. Without batching each
#: triple costs two full round-trips, which dominates the load time.
DEFAULT_BATCH_SIZE = 10000

#: Seconds a download may go without receiving anything before it is given up.
DOWNLOAD_TIMEOUT = 60

DOWNLOAD_CHUNK_SIZE = 1024 * 1024


class DamagedDumpError(RuntimeError):
    """A cached dump turned out to be incomplete or corrupt while loading."""

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
            print('-- downloading {} to {}'.format(source.url, skos_file))

        # Only now, so nothing is written until there is something to write
        paths.ensure_data_dir()

        # The dump only takes its real name once it is complete and verified.
        # load() uses any file of that name as it is, so a partial download
        # left there would fail every later load (#27).
        partial = paths.partial_name(skos_file)

        try:
            target = open(partial, 'xb')
        except OSError as exc:
            raise paths.unwritable(os.path.dirname(skos_file), exc) from exc

        try:
            with target:
                received, expected = self._fetch(source.url, target)

            if expected is not None and received != expected:
                raise RuntimeError(
                    'The download of the {!r} dump from {} ended early: got '
                    '{} of {} bytes. Nothing was cached; run load() again to '
                    'retry.'.format(normalized_language, source.url, received, expected))

            # The Databus publishes a checksum per file; the wiki archive does not.
            if source.sha256:
                digest = self._sha256(partial)

                if digest != source.sha256:
                    raise RuntimeError(
                        'Checksum mismatch for the {!r} dump downloaded from {}: '
                        'expected {}, got {}. The file has been discarded.'.format(
                            normalized_language, source.url, source.sha256, digest))

                if verbose:
                    print('Checksum verified ({})'.format(digest[:16]))

            os.replace(partial, skos_file)

        except error.HTTPError as http_error:
            raise RuntimeError(
                'Could not download the SKOS dump for language {!r} from {} '
                '({}). The {!r} engine may no longer serve this file.'.format(
                    normalized_language, source.url, http_error, engine)) from http_error

        except (OSError, http.client.HTTPException) as interrupted:
            # A refused or dropped connection, a timeout, a full disk
            raise RuntimeError(
                'The download of the {!r} dump from {} was interrupted ({!r}). '
                'Nothing was cached; run load() again to retry.'.format(
                    normalized_language, source.url, interrupted)) from interrupted

        finally:
            # Whatever went wrong, KeyboardInterrupt included
            self._discard(partial)

        if verbose:
            print("Finished downloading {} file".format(skos_file))

    @staticmethod
    def _fetch(url, target):
        """Stream ``url`` into the open file ``target``.

        Returns:
            tuple: Bytes received, and bytes announced (None if unannounced).
        """
        with request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as response:
            announced = response.headers.get('Content-Length')
            expected = int(announced) if announced and announced.isdigit() else None
            received = 0

            for chunk in iter(lambda: response.read(DOWNLOAD_CHUNK_SIZE), b''):
                target.write(chunk)
                received += len(chunk)

        return received, expected

    @staticmethod
    def _discard(path):
        paths.discard(path)

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
            db (:obj:`Redis`, optional): Custom Redis client. It is used as it
                is: whatever db it points at holds this object's language.
            language (:obj:`str`, optional): Choose the default language, by its
                code (``'de'``), ISO 639-2 code (``'ger'``), locale (``'de-DE'``)
                or DBpedia code (``'uk'`` for Ukrainian).
            engine (:obj:`str`, optional): Where dumps are downloaded from. Defaults to
                ``'wiki-archive'``. See :mod:`fastcat.engines`.
            kwargs (:obj:`dict`, optional): Any arguments, which you wish to pass to the Redis client.

        Raises:
            ValueError: The engine name or the language is not recognised.
            RuntimeError: The language has no db yet, and the mapping that
                gives it one cannot be saved, because fastcat's data
                directory (:meth:`get_data_dir`) is not writable.

        """

        super(FastCatBase, self).__init__()

        # Fail before touching redis (or the slot store) if the caller asked
        # for an engine that cannot download anything, or a language fastcat
        # does not support
        validate_engine(engine)
        self.engine = engine

        if language is not None:
            language = resolve_language(language)

        # Load most recent language-redis mapping
        store.load_settings()
        _adopt_legacy_dumps_once()

        # Anything not set here is left at the redis client's own default
        options = {'host': DEFAULT_REDIS_HOST, 'port': DEFAULT_REDIS_PORT}
        options.update(kwargs)

        # Initialize redis client object
        if db is None:

            if language is None:

                # Check if language-redis mapping is ok
                assert 'en' in store.languages

                # Initialize connection for English dataset
                db = redis.Redis(**options)  # default is db=0
                language = 'en'
            else:

                # Initialize connection for any other language dataset
                try:
                    slot = store.get_slot(language)
                except ValueError:
                    slot = store.save_settings(language)

                db = redis.Redis(db=slot, **options)

        # There must be always only one redis client
        self.db = db

        # The language load() fills this db with and get_current_language()
        # reports. Given explicitly, it holds even for a client of the caller's
        # own, whatever db that points at (#23). Left out with such a client,
        # it is None and looked up from the client's db slot instead.
        self.language = language

    def switch_language(self, language):
        """Switch language on an existing FastCat object.

        The object moves to the language's own db on the same Redis server,
        keeping its connection settings (host, port, password, SSL, ...),
        those of a client passed in as ``db`` included. A language with no
        db yet is given one and loaded.

        Raises:
            ValueError: The language is not recognised.
        """
        language = resolve_language(language)

        try:
            slot = store.get_slot(language)
            new = False
        except ValueError:
            slot = store.save_settings(language)
            new = True

        self.db = self._client_on(slot)
        self.language = language

        if new:
            self.load(language)

    def _client_on(self, slot):
        """A client on db ``slot`` of the server this object is connected to.

        Built from the current client's connection pool, so whatever that was
        set up with (host, port, password, SSL, a unix socket, timeouts)
        carries over. It used to be rebuilt from the constructor's keyword
        arguments, which a client passed in as ``db`` leaves empty, so it
        reconnected to localhost:6379 (#28).
        """
        pool = self.db.connection_pool

        return redis.Redis(connection_pool=redis.ConnectionPool(
            connection_class=pool.connection_class,
            max_connections=pool.max_connections,
            **dict(pool.connection_kwargs, db=slot)))

    def get_current_language(self):
        """Get current language, as a pycountry record, or None if unknown.

        That is the language given to the constructor (or to
        :meth:`switch_language`), and otherwise whichever language the slot
        store assigns to the client's db.
        """
        language = self._language_id()

        return None if language is None else store.language_info(language)

    def _db_index(self):
        return self.db.connection_pool.connection_kwargs.get('db', 0)

    def _language_id(self):
        """The fastcat id of this object's language, or None if unknown."""
        if self.language is not None:
            return self.language

        return store.get_language_id(self._db_index())

    @staticmethod
    def get_supported_languages():
        """Get list of supported languages."""
        return languages.available_languages.keys()

    @staticmethod
    def get_data_dir():
        """Get the directory fastcat keeps its downloaded dumps and its
        language -> Redis db mapping in.

        That is the ``FASTCAT_DATA_DIR`` environment variable if it is set,
        and otherwise the user's cache directory: ``~/.cache/fastcat`` on
        Linux, ``~/Library/Caches/fastcat`` on macOS and
        ``%LOCALAPPDATA%\\fastcat\\Cache`` on Windows. It is created on first
        use.
        """
        return paths.data_dir()

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

    def _loaded_language(self):
        """Which language populates this redis db, or None if that is unknown.

        Unknown means the db is empty, or was loaded before the language was
        recorded (0.3.3).
        """
        if not self.db.get("loaded-skos"):
            return None

        recorded = self.db.get("loaded-language")

        if recorded is None:
            return None

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
            ValueError: ``batch_size`` is smaller than 1, or the language is
                not recognised or cannot be worked out.
            RuntimeError: The db already holds another language, or the same
                language from another engine. Also raised when the download
                fails or is interrupted, and when the cached dump turns out
                to be damaged (:class:`DamagedDumpError`). Nothing broken is
                left in the cache, so calling ``load()`` again downloads the
                dump afresh.
        """
        if batch_size < 1:
            raise ValueError(
                'batch_size must be at least 1, got {!r}'.format(batch_size))

        if language is None:
            language = self._language_id()

            if language is None:
                raise ValueError(
                    'No language to load: this client is on redis db {}, which '
                    'no language is assigned to. Name one, e.g. '
                    'FastCat(db=client, language=\'et\') or '
                    'load(language=\'et\').'.format(self._db_index()))
        else:
            # Everything below (the cache file name, the category-prefix
            # pattern) keys on the normalised id, so 'uk' or 'pt-BR' would
            # otherwise get as far as the download and then fail
            language = resolve_language(language)

        if engine is None:
            engine = self.engine
        validate_engine(engine)

        loaded_engine = self._loaded_engine()

        if loaded_engine is not None:
            loaded_language = self._loaded_language()

            if loaded_language is not None and loaded_language != language:
                # Otherwise the load would be skipped below as "already
                # loaded", and this language's lookups answered from another
                raise RuntimeError(
                    'This redis db already holds {!r} categories, so it cannot '
                    'also hold {!r}. Flush it first (e.g. FastCat.db.flushdb()) '
                    'or use another db for {!r}.'.format(
                        loaded_language, language, language))

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

        try:
            self._insert(skos_file, language, verbose, progress_bar, batch_size)
        except DamagedDumpError:
            # Only now that the file is closed (Windows cannot delete an open
            # file), so the next load() downloads the dump afresh
            self._discard(skos_file)
            raise

        # Only once every triple is in, so an interrupted load is not mistaken
        # for a complete one
        self.db.set("loaded-skos", "1")
        self.db.set("loaded-engine", engine)
        self.db.set("loaded-language", language)

    def _insert(self, skos_file, language, verbose, progress_bar, batch_size):
        """Stream a dump's broader relations into Redis as b:/n: pairs.

        Raises:
            DamagedDumpError: The dump turned out to be truncated or corrupt.
        """
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

            for line in self._lines(uncompressed, skos_file):

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

    @staticmethod
    def _lines(uncompressed, skos_file):
        """The lines of an open dump, reporting a damaged one as such.

        A dump cut short (as 0.3.3 and earlier could leave behind, #27) only
        shows up once decompression reaches the end of it.
        """
        try:
            yield from uncompressed
        except (EOFError, OSError) as damaged:
            raise DamagedDumpError(
                'The cached dump {} is incomplete or damaged ({}), so it has '
                'been deleted. Run load() again to download it afresh.'.format(
                    skos_file, damaged)) from damaged
