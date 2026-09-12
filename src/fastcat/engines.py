"""Sources fastcat can download Wikipedia SKOS dumps from.

fastcat used to pull from ``downloads.dbpedia.org/current/``. DBpedia retired
that tree and every URL under it now returns 404, which broke ``load()``
outright.

Two sources replace it:

``wiki-archive``
    The archived static releases, pinned to the 2016-10 release linked from
    DBpedia's `wiki archive
    <https://downloads.dbpedia.org/wiki-archive/dbpedia-version-2016-10.html>`_.
    Fixed URLs, no metadata lookup, and no network access beyond the download
    itself. The trade-off is data vintage: the categories are a snapshot of
    Wikipedia as of 2016.

``databus``
    DBpedia's current distribution channel. Files are not at fixed paths;
    they are described by metadata on the `Databus
    <https://databus.dbpedia.org/>`_, so fetching one means resolving the
    artifact's newest version and finding the part for the wanted language.
    Slower to start and dependent on the Databus being up, but the data is
    current -- the 2022.12.01 release rather than 2016.

Both serve the same n-triples-in-bzip2 shape, so nothing downstream of the
download cares which was used.
"""

import json
import time
from collections import namedtuple
from urllib import error, request

WIKI_ARCHIVE = 'wiki-archive'
DATABUS = 'databus'

#: Every engine name fastcat recognises.
available_engines = (WIKI_ARCHIVE, DATABUS)

#: The engines that can actually download something.
implemented_engines = (WIKI_ARCHIVE, DATABUS)

DEFAULT_ENGINE = WIKI_ARCHIVE

#: Archived release the wiki-archive engine is pinned to.
WIKI_ARCHIVE_RELEASE = '2016-10'

WIKI_ARCHIVE_URL_PATTERN = (
    'https://downloads.dbpedia.org/{release}/core-i18n/{mapping}/'
    'skos_categories_{mapping}.ttl.bz2'
)

#: Databus artifact holding the category dumps, one part per language.
DATABUS_ARTIFACT = 'https://databus.dbpedia.org/dbpedia/generic/categories'

#: Databus content variant selecting the SKOS parts. The same artifact also
#: carries ``articles`` parts, which are a different dataset.
DATABUS_TAG = 'skos'

DATABUS_TIMEOUT = 60

#: Metadata lookups go over the network and the Databus does occasionally
#: blip, so a failed fetch is retried rather than failing the whole load.
DATABUS_ATTEMPTS = 3
DATABUS_RETRY_WAIT = 2

#: What a download needs: where to get it, and what it should hash to. The
#: wiki archive publishes no checksums, so ``sha256`` is None there.
DownloadSource = namedtuple('DownloadSource', ['url', 'sha256'])

# Databus metadata is stable within a run and costs a request each, so it is
# fetched once. Call clear_cache() to force a re-read.
_metadata_cache = {}


class EngineError(RuntimeError):
    """An engine could not work out where to download a dump from."""


def validate_engine(engine):
    """Check an engine name, raising if it is unknown or not implemented yet.

    Args:
        engine (str): Engine name, e.g. ``'wiki-archive'``.

    Raises:
        ValueError: The name is not one of :data:`available_engines`.
        NotImplementedError: The engine is known but not implemented yet.
    """
    if engine not in available_engines:
        raise ValueError(
            'Unknown engine {!r}. Supported engines: {}.'.format(
                engine, ', '.join(available_engines)))

    if engine not in implemented_engines:
        raise NotImplementedError(
            'The {!r} engine is not implemented yet. Use {!r} instead '
            '(the default).'.format(engine, DEFAULT_ENGINE))


def clear_cache():
    """Forget cached Databus metadata."""
    _metadata_cache.clear()


def _fetch_json(url, attempts=DATABUS_ATTEMPTS):
    """Fetch a Databus JSON-LD document, retrying transient failures.

    Kept separate so tests can stand in for the network.
    """
    req = request.Request(url, headers={'Accept': 'application/ld+json'})
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            with request.urlopen(req, timeout=DATABUS_TIMEOUT) as response:
                return json.loads(response.read().decode('utf-8'))
        except error.URLError as url_error:
            last_error = url_error
        except ValueError as decode_error:
            # A truncated or half-served response reads as bad JSON, which is
            # just as transient as a refused connection
            last_error = decode_error

        if attempt < attempts:
            time.sleep(DATABUS_RETRY_WAIT * attempt)

    raise EngineError(
        'Could not read DBpedia Databus metadata at {} after {} attempts '
        '({}).'.format(url, attempts, last_error)) from last_error


def _cached_json(url):
    if url not in _metadata_cache:
        _metadata_cache[url] = _fetch_json(url)
    return _metadata_cache[url]


def latest_databus_version(artifact=DATABUS_ARTIFACT):
    """Return the newest version of a Databus artifact, e.g. ``'2022.12.01'``.

    Versions are dotted dates, so the newest is the largest string.
    """
    document = _cached_json(artifact)
    versions = [
        entry['@id'].rsplit('/', 1)[-1]
        for entry in document.get('databus:hasVersion', [])
        if '@id' in entry
    ]

    if not versions:
        raise EngineError(
            'The Databus artifact {} lists no versions.'.format(artifact))

    return max(versions)


def databus_parts(version, artifact=DATABUS_ARTIFACT):
    """Return the ``Part`` entries of one artifact version."""
    document = _cached_json('{}/{}'.format(artifact, version))

    return [node for node in document.get('@graph', [])
            if node.get('@type') == 'Part']


def databus_source(wikipedia_mapping, version=None, artifact=DATABUS_ARTIFACT):
    """Resolve a language's SKOS dump on the Databus.

    Args:
        wikipedia_mapping (str): DBpedia language code, i.e. the
            ``wikipedia_mapping`` of a :mod:`fastcat.lang` entry.
        version (:obj:`str`, optional): Artifact version such as
            ``'2022.12.01'``. Defaults to the newest published version.
        artifact (:obj:`str`, optional): Databus artifact to look in.

    Returns:
        DownloadSource: The download URL and its published sha256.

    Raises:
        EngineError: The Databus is unreachable, or has no SKOS part for this
            language.
    """
    if version is None:
        version = latest_databus_version(artifact)

    for part in databus_parts(version, artifact):
        if (part.get('dcv:lang') == wikipedia_mapping
                and part.get('dcv:tag') == DATABUS_TAG
                and part.get('downloadURL')):
            return DownloadSource(url=part['downloadURL'],
                                  sha256=part.get('sha256sum'))

    raise EngineError(
        'The Databus release {} has no {!r} part for language {!r}.'.format(
            version, DATABUS_TAG, wikipedia_mapping))


def skos_source(wikipedia_mapping, engine=DEFAULT_ENGINE, version=None):
    """Work out where to download a language's SKOS categories dump.

    Args:
        wikipedia_mapping (str): DBpedia subdomain/language code for the
            language. Note this is not always the same as the fastcat language
            id -- Ukrainian is ``ua`` but lives under ``uk``.
        engine (:obj:`str`, optional): Which source to resolve against.
        version (:obj:`str`, optional): Databus artifact version; ignored by
            the wiki-archive engine, which is pinned to one release.

    Returns:
        DownloadSource: The download URL, and a sha256 when the engine
        publishes one.
    """
    validate_engine(engine)

    if engine == DATABUS:
        return databus_source(wikipedia_mapping, version=version)

    return DownloadSource(
        url=WIKI_ARCHIVE_URL_PATTERN.format(release=WIKI_ARCHIVE_RELEASE,
                                            mapping=wikipedia_mapping),
        sha256=None)


def skos_url(wikipedia_mapping, engine=DEFAULT_ENGINE, version=None):
    """Download URL of a language's SKOS categories dump.

    Thin wrapper over :func:`skos_source` for callers that only want the URL.
    """
    return skos_source(wikipedia_mapping, engine=engine, version=version).url
