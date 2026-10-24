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
    The part is looked up through the Databus SPARQL endpoint, with the
    version's JSON-LD document as the fallback. Slower to start and dependent
    on the Databus being up, but the data is current -- the 2022.12.01
    release rather than 2016.

Both serve the same n-triples-in-bzip2 shape, so nothing downstream of the
download cares which was used.
"""

import http.client
import json
import re
import time
from collections import namedtuple
from urllib import parse, request

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

#: Databus SPARQL endpoint. Asking it for one part takes a few hundred bytes;
#: a version's JSON-LD document describes every part of every language, about
#: 384 KB, and the Databus has taken to cutting it short (#26).
DATABUS_SPARQL = 'https://databus.dbpedia.org/sparql'

DATABUS_TIMEOUT = 60

#: Metadata lookups go over the network and the Databus does occasionally
#: blip, so a failed fetch is retried rather than failing the whole load.
DATABUS_ATTEMPTS = 3
DATABUS_RETRY_WAIT = 2

#: Failures worth another try: network errors (URLError and timeouts are
#: OSErrors), a response cut short (http.client.IncompleteRead) and a
#: half-served body that does not parse as JSON (ValueError).
_TRANSIENT_ERRORS = (OSError, http.client.HTTPException, ValueError)

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


def _fetch(req, what, attempts=DATABUS_ATTEMPTS):
    """Fetch and parse a JSON response, retrying transient failures.

    Args:
        req (urllib.request.Request): The request to send.
        what (str): What is being read, for the error message.
        attempts (int): How many times to try.

    Raises:
        EngineError: Every attempt failed.
    """
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            with request.urlopen(req, timeout=DATABUS_TIMEOUT) as response:
                return json.loads(response.read().decode('utf-8'))
        except _TRANSIENT_ERRORS as transient:
            last_error = transient

        if attempt < attempts:
            time.sleep(DATABUS_RETRY_WAIT * attempt)

    raise EngineError(
        'Could not read {} after {} attempts ({!r}).'.format(
            what, attempts, last_error)) from last_error


def _fetch_json(url, attempts=DATABUS_ATTEMPTS):
    """Fetch a Databus JSON-LD document, retrying transient failures.

    Kept separate so tests can stand in for the network.
    """
    req = request.Request(url, headers={'Accept': 'application/ld+json'})

    return _fetch(req, 'DBpedia Databus metadata at {}'.format(url), attempts)


def _fetch_sparql(query, attempts=DATABUS_ATTEMPTS):
    """Run a query on the Databus SPARQL endpoint and return its result rows.

    Kept separate so tests can stand in for the network.
    """
    req = request.Request(
        DATABUS_SPARQL,
        data=parse.urlencode({'query': query}).encode('utf-8'),
        headers={'Accept': 'application/sparql-results+json'})

    document = _fetch(req, 'the DBpedia Databus SPARQL endpoint', attempts)

    try:
        return document['results']['bindings']
    except (KeyError, TypeError) as malformed:
        raise EngineError(
            'The DBpedia Databus SPARQL endpoint gave an answer without '
            'result rows: {!r}'.format(document)[:300]) from malformed


def _cached_json(url):
    if url not in _metadata_cache:
        _metadata_cache[url] = _fetch_json(url)
    return _metadata_cache[url]


def _cached_sparql(query):
    key = ('sparql', query)
    if key not in _metadata_cache:
        _metadata_cache[key] = _fetch_sparql(query)
    return _metadata_cache[key]


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


_SPARQL_PART_QUERY = '''\
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX databus: <https://dataid.dbpedia.org/databus#>
PREFIX dcv: <https://dataid.dbpedia.org/databus-cv#>
SELECT ?url ?sha256 WHERE {{
  <{version}> dcat:distribution ?part .
  ?part dcv:lang {lang} ;
        dcv:tag {tag} ;
        dcat:downloadURL ?url .
  OPTIONAL {{ ?part databus:sha256sum ?sha256 }}
}}
ORDER BY ?url'''


def _sparql_string(value):
    """``value`` as a SPARQL string literal."""
    return '"{}"'.format(value.replace('\\', '\\\\').replace('"', '\\"'))


def databus_sparql_source(wikipedia_mapping, version, artifact=DATABUS_ARTIFACT):
    """Look a language's SKOS part up through the Databus SPARQL endpoint.

    Args:
        wikipedia_mapping (str): DBpedia language code.
        version (str): Artifact version such as ``'2022.12.01'``.
        artifact (:obj:`str`, optional): Databus artifact to look in.

    Returns:
        DownloadSource: The download URL and its published sha256, or None if
        the endpoint lists no such part.

    Raises:
        ValueError: ``version`` is not a plain version string.
        EngineError: The endpoint could not be read.
    """
    # It goes into an IRI in the query, so nothing but a version will do
    if not re.fullmatch(r'[\w.-]+', version):
        raise ValueError('Not a Databus version: {!r}'.format(version))

    query = _SPARQL_PART_QUERY.format(
        version='{}/{}'.format(artifact, version),
        lang=_sparql_string(wikipedia_mapping),
        tag=_sparql_string(DATABUS_TAG))

    for row in _cached_sparql(query):
        url = row.get('url', {}).get('value')

        if url:
            return DownloadSource(url=url,
                                  sha256=row.get('sha256', {}).get('value'))

    return None


def databus_source(wikipedia_mapping, version=None, artifact=DATABUS_ARTIFACT):
    """Resolve a language's SKOS dump on the Databus.

    The part is looked up through the Databus SPARQL endpoint, which answers
    in a few hundred bytes. If that fails or finds nothing, the version's
    JSON-LD document, which lists every part, is searched instead.

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

    sparql_error = None

    try:
        source = databus_sparql_source(wikipedia_mapping, version, artifact)
    except EngineError as failure:
        source, sparql_error = None, failure

    if source is not None:
        return source

    try:
        parts = databus_parts(version, artifact)
    except EngineError as document_error:
        if sparql_error is None:
            # The endpoint answered, just without this part
            raise EngineError(
                'The Databus release {} has no {!r} part for language {!r} '
                'according to its SPARQL endpoint, and the release metadata '
                'could not be read to double-check: {}'.format(
                    version, DATABUS_TAG, wikipedia_mapping,
                    document_error)) from document_error

        raise EngineError(
            'Could not look up the {!r} dump for language {!r} on the '
            'Databus. Its SPARQL endpoint failed ({}), and so did the '
            'release metadata ({}).'.format(
                DATABUS_TAG, wikipedia_mapping, sparql_error,
                document_error)) from document_error

    for part in parts:
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
