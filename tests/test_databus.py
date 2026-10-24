"""Checks on the Databus engine.

The offline tests stand in for the Databus by replacing the JSON and SPARQL
fetches, so the resolution logic (newest version, right language, right
content variant) is covered without network access. The integration tests hit
the real Databus.
"""

import http.client
import json
import re
from urllib import parse

import pytest

import fastcat.engines as engines
from fastcat.engines import DATABUS, DownloadSource, EngineError, skos_source
from fastcat.interface import FastCat
from language_cases import LANGUAGE_CASES

ARTIFACT = engines.DATABUS_ARTIFACT

ARTIFACT_DOC = {
    '@id': ARTIFACT,
    'databus:hasVersion': [
        {'@id': ARTIFACT + '/2020.02.01'},
        {'@id': ARTIFACT + '/2022.12.01'},
        {'@id': ARTIFACT + '/2022.03.01'},
    ],
}


def _part(lang, tag, url, sha='a' * 64):
    return {'@type': 'Part', 'dcv:lang': lang, 'dcv:tag': tag,
            'downloadURL': url, 'sha256sum': sha}


VERSION_DOC = {
    '@graph': [
        {'@id': ARTIFACT, '@type': 'Artifact'},
        _part('en', 'skos', 'https://downloads.example/categories_lang=en_skos.ttl.bz2', 'e' * 64),
        _part('en', 'articles', 'https://downloads.example/categories_lang=en_articles.ttl.bz2'),
        _part('uk', 'skos', 'https://downloads.example/categories_lang=uk_skos.ttl.bz2', 'u' * 64),
    ],
}

OLD_VERSION_DOC = {
    '@graph': [
        _part('en', 'skos', 'https://downloads.example/old_en_skos.ttl.bz2', 'o' * 64),
    ],
}


DOCUMENTS = {
    ARTIFACT: ARTIFACT_DOC,
    ARTIFACT + '/2022.12.01': VERSION_DOC,
    ARTIFACT + '/2022.03.01': OLD_VERSION_DOC,
}


@pytest.fixture
def databus(monkeypatch):
    """Serve canned Databus metadata, and record what was requested.

    The SPARQL endpoint is down here, so lookups take the fallback through
    the version documents. The ``sparql`` fixture brings it up.
    """
    requested = []

    def fake_fetch(url):
        requested.append(url)
        try:
            return DOCUMENTS[url]
        except KeyError:
            raise engines.EngineError('no such document: ' + url)

    def sparql_down(query):
        raise engines.EngineError('SPARQL endpoint down in this test')

    engines.clear_cache()
    monkeypatch.setattr(engines, '_fetch_json', fake_fetch)
    monkeypatch.setattr(engines, '_fetch_sparql', sparql_down)
    yield requested
    engines.clear_cache()


def _answer(query):
    """What the Databus SPARQL endpoint would answer, from the canned documents."""
    version = re.search(r'<([^>]+)> dcat:distribution', query).group(1)
    lang = re.search(r'dcv:lang "([^"]*)"', query).group(1)
    tag = re.search(r'dcv:tag "([^"]*)"', query).group(1)

    return [{'url': {'type': 'uri', 'value': part['downloadURL']},
             'sha256': {'type': 'literal', 'value': part['sha256sum']}}
            for part in DOCUMENTS.get(version, {}).get('@graph', [])
            if part.get('@type') == 'Part'
            and part['dcv:lang'] == lang and part['dcv:tag'] == tag]


@pytest.fixture
def sparql(databus, monkeypatch):
    """Bring the SPARQL endpoint up; returns the queries it was sent."""
    queries = []

    def fake_sparql(query):
        queries.append(query)
        return _answer(query)

    monkeypatch.setattr(engines, '_fetch_sparql', fake_sparql)
    return queries


class Response:
    """A urlopen() response whose body is cut short ``short`` times first."""

    def __init__(self, body, short=0):
        self.body = body
        self.short = short

    def read(self):
        if self.short:
            self.short -= 1
            raise http.client.IncompleteRead(self.body[:10], len(self.body) - 10)
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_the_newest_version_is_chosen(databus):
    assert engines.latest_databus_version() == '2022.12.01'


def test_source_resolves_url_and_checksum(databus):
    source = skos_source('en', engine=DATABUS)

    assert source == DownloadSource(
        url='https://downloads.example/categories_lang=en_skos.ttl.bz2',
        sha256='e' * 64)


def test_the_articles_variant_is_not_mistaken_for_skos(databus):
    assert 'skos' in skos_source('en', engine=DATABUS).url
    assert 'articles' not in skos_source('en', engine=DATABUS).url


def test_the_dbpedia_code_is_used_not_the_fastcat_id(databus):
    # Ukrainian is 'ua' in fastcat but 'uk' on the Databus
    assert skos_source('uk', engine=DATABUS).url.endswith('lang=uk_skos.ttl.bz2')


def test_an_explicit_version_is_honoured(databus):
    source = engines.databus_source('en', version='2022.03.01')

    assert source.url == 'https://downloads.example/old_en_skos.ttl.bz2'


def test_a_language_the_databus_lacks_is_reported(databus):
    with pytest.raises(EngineError, match='no .* part for language'):
        skos_source('kl', engine=DATABUS)


def test_metadata_is_fetched_once_per_document(databus):
    skos_source('en', engine=DATABUS)
    skos_source('uk', engine=DATABUS)

    assert databus.count(ARTIFACT) == 1
    assert databus.count(ARTIFACT + '/2022.12.01') == 1


def test_clearing_the_cache_forces_a_refetch(databus):
    skos_source('en', engine=DATABUS)
    engines.clear_cache()
    skos_source('en', engine=DATABUS)

    assert databus.count(ARTIFACT) == 2


def test_an_artifact_without_versions_is_reported(monkeypatch):
    engines.clear_cache()
    monkeypatch.setattr(engines, '_fetch_json', lambda url: {'@id': ARTIFACT})

    with pytest.raises(EngineError, match='lists no versions'):
        engines.latest_databus_version()

    engines.clear_cache()


def test_an_unreachable_databus_is_reported(monkeypatch):
    from urllib import error as urllib_error

    engines.clear_cache()
    monkeypatch.setattr(engines.time, 'sleep', lambda seconds: None)

    def explode(request, timeout=None):
        raise urllib_error.URLError('connection refused')

    monkeypatch.setattr(engines.request, 'urlopen', explode)

    with pytest.raises(EngineError, match='after 3 attempts'):
        engines.latest_databus_version()

    engines.clear_cache()


def test_a_transient_failure_is_retried(monkeypatch):
    """One blip should not fail a load -- this bit the suite for real once."""
    from urllib import error as urllib_error

    engines.clear_cache()
    monkeypatch.setattr(engines.time, 'sleep', lambda seconds: None)

    calls = []

    class Response:
        def read(self):
            return b'{"@id": "x", "databus:hasVersion": [{"@id": "a/2022.12.01"}]}'

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def flaky(request, timeout=None):
        calls.append(1)
        if len(calls) < 3:
            raise urllib_error.URLError('temporarily unavailable')
        return Response()

    monkeypatch.setattr(engines.request, 'urlopen', flaky)

    assert engines.latest_databus_version() == '2022.12.01'
    assert len(calls) == 3

    engines.clear_cache()


def test_retries_are_bounded(monkeypatch):
    from urllib import error as urllib_error

    engines.clear_cache()
    monkeypatch.setattr(engines.time, 'sleep', lambda seconds: None)

    calls = []

    def explode(request, timeout=None):
        calls.append(1)
        raise urllib_error.URLError('down')

    monkeypatch.setattr(engines.request, 'urlopen', explode)

    with pytest.raises(EngineError):
        engines.latest_databus_version()

    assert len(calls) == engines.DATABUS_ATTEMPTS

    engines.clear_cache()


# --- responses cut short (#26) ------------------------------------------------

def test_a_response_cut_short_is_retried(monkeypatch):
    engines.clear_cache()
    monkeypatch.setattr(engines.time, 'sleep', lambda seconds: None)

    body = json.dumps({'databus:hasVersion': [{'@id': ARTIFACT + '/2022.12.01'}]})
    response = Response(body.encode('utf-8'), short=2)
    calls = []

    def urlopen(request, timeout=None):
        calls.append(1)
        return response

    monkeypatch.setattr(engines.request, 'urlopen', urlopen)

    assert engines.latest_databus_version() == '2022.12.01'
    assert len(calls) == 3

    engines.clear_cache()


def test_a_response_always_cut_short_is_an_engine_error(monkeypatch):
    # It used to escape as a bare http.client.IncompleteRead, unretried
    engines.clear_cache()
    monkeypatch.setattr(engines.time, 'sleep', lambda seconds: None)

    response = Response(b'{"@graph": []}', short=engines.DATABUS_ATTEMPTS)
    monkeypatch.setattr(engines.request, 'urlopen', lambda request, timeout=None: response)

    with pytest.raises(EngineError, match='after 3 attempts.*IncompleteRead'):
        engines.databus_parts('2022.12.01')

    engines.clear_cache()


# --- the SPARQL lookup (#26) --------------------------------------------------

def test_sparql_resolves_url_and_checksum_without_the_version_document(sparql, databus):
    source = skos_source('en', engine=DATABUS)

    assert source == DownloadSource(
        url='https://downloads.example/categories_lang=en_skos.ttl.bz2',
        sha256='e' * 64)
    # Only the small artifact document; the version document is not needed
    assert databus == [ARTIFACT]


def test_the_query_names_the_release_the_language_and_the_variant(sparql):
    skos_source('uk', engine=DATABUS)

    (query,) = sparql
    assert '<{}/2022.12.01> dcat:distribution'.format(ARTIFACT) in query
    assert 'dcv:lang "uk"' in query
    assert 'dcv:tag "skos"' in query


def test_sparql_honours_an_explicit_version(sparql):
    source = engines.databus_source('en', version='2022.03.01')

    assert source.url == 'https://downloads.example/old_en_skos.ttl.bz2'


def test_sparql_answers_are_cached(sparql):
    skos_source('en', engine=DATABUS)
    skos_source('en', engine=DATABUS)

    assert len(sparql) == 1


def test_a_version_that_is_not_one_is_refused(sparql):
    with pytest.raises(ValueError, match='Not a Databus version'):
        engines.databus_sparql_source('en', '2022.12.01> } #')


def test_the_version_document_is_the_fallback_when_sparql_fails(databus):
    # The databus fixture keeps the SPARQL endpoint down
    source = skos_source('en', engine=DATABUS)

    assert source.sha256 == 'e' * 64
    assert ARTIFACT + '/2022.12.01' in databus


def test_the_version_document_is_the_fallback_when_sparql_finds_nothing(databus, monkeypatch):
    monkeypatch.setattr(engines, '_fetch_sparql', lambda query: [])

    source = skos_source('en', engine=DATABUS)

    assert source.url == 'https://downloads.example/categories_lang=en_skos.ttl.bz2'


def test_sparql_and_the_document_both_failing_is_one_error(databus):
    with pytest.raises(EngineError) as excinfo:
        engines.databus_source('en', version='2099.01.01')

    message = str(excinfo.value)
    assert 'SPARQL endpoint down' in message
    assert 'no such document' in message


def test_the_sparql_request(monkeypatch):
    sent = []
    answer = {'head': {'vars': ['url', 'sha256']},
              'results': {'bindings': [{'url': {'type': 'uri', 'value': 'https://x/y'}}]}}

    def urlopen(request, timeout=None):
        sent.append(request)
        return Response(json.dumps(answer).encode('utf-8'))

    monkeypatch.setattr(engines.request, 'urlopen', urlopen)

    assert engines._fetch_sparql('SELECT * WHERE {}') == answer['results']['bindings']

    (request,) = sent
    assert request.full_url == engines.DATABUS_SPARQL
    assert request.get_header('Accept') == 'application/sparql-results+json'
    assert parse.parse_qs(request.data.decode('utf-8')) == {'query': ['SELECT * WHERE {}']}


def test_a_sparql_answer_without_rows_is_an_engine_error(monkeypatch):
    monkeypatch.setattr(engines.request, 'urlopen',
                        lambda request, timeout=None: Response(b'{"boolean": true}'))

    with pytest.raises(EngineError, match='without result rows'):
        engines._fetch_sparql('ASK {}')


def test_the_client_carries_the_engine_into_loading(databus):
    client = FastCat(engine=DATABUS)

    assert client.engine == DATABUS


# --- against the real Databus -------------------------------------------------

@pytest.mark.integration
def test_the_real_databus_publishes_a_version():
    engines.clear_cache()
    version = engines.latest_databus_version()

    # Versions are dotted dates, and the artifact has been published since 2018
    assert version >= '2022.12.01'


@pytest.mark.integration
@pytest.mark.parametrize('case', LANGUAGE_CASES, ids=lambda c: c.language)
def test_every_supported_language_resolves_on_the_real_databus(case):
    import fastcat.lang as languages

    mapping = next(language.wikipedia_mapping
                   for language in languages.available_languages.values()
                   if language.id == case.language)

    source = skos_source(mapping, engine=DATABUS)

    assert source.url.endswith('lang={}_skos.ttl.bz2'.format(mapping))
    assert len(source.sha256) == 64


@pytest.mark.integration
@pytest.mark.parametrize('case', LANGUAGE_CASES, ids=lambda c: c.language)
def test_every_supported_language_resolves_through_the_real_sparql_endpoint(case):
    import fastcat.lang as languages

    mapping = next(language.wikipedia_mapping
                   for language in languages.available_languages.values()
                   if language.id == case.language)

    engines.clear_cache()
    source = engines.databus_sparql_source(mapping, '2022.12.01')

    assert source.url == (
        'https://downloads.dbpedia.org/repo/dbpedia/generic/categories/'
        '2022.12.01/categories_lang={}_skos.ttl.bz2'.format(mapping))
    assert len(source.sha256) == 64


@pytest.mark.integration
def test_loading_a_language_from_the_real_databus():
    """Download, verify, load and query current Databus data.

    Uses a scratch Redis db of its own: the language's usual slot may already
    hold wiki-archive data, and mixing the two is exactly what fastcat refuses
    to do.
    """
    import redis

    from fastcat.engines import WIKI_ARCHIVE
    from fastcat.interface import DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT

    client = redis.Redis(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT, db=15)
    client.flushdb()

    try:
        categories = FastCat(db=client, engine=DATABUS)
        categories.load(language='et', progress_bar=False)

        assert client.dbsize() > 10000
        assert client.get('loaded-engine') == b'databus'

        # Every broader edge must have its narrower counterpart. Checking the
        # invariant beats asserting category names, which legitimately differ
        # between the 2016 archive and current Databus data.
        checked = 0
        for key in client.scan_iter(match='b:*', count=500):
            category = key.decode('utf-8')[2:]
            for broader in categories.broader(category):
                assert category in categories.narrower(broader)
            checked += 1
            if checked >= 100:
                break

        assert checked == 100

        # Loading the other engine on top of this must be refused
        with pytest.raises(RuntimeError, match='merge two different snapshots'):
            categories.load(language='et', engine=WIKI_ARCHIVE, progress_bar=False)
    finally:
        client.flushdb()
