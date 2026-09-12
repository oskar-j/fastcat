"""Sources fastcat can download Wikipedia SKOS dumps from.

fastcat used to pull from ``downloads.dbpedia.org/current/``. DBpedia retired
that tree and every URL under it now returns 404, which broke ``load()``
outright.

Two replacements exist:

``wiki-archive``
    The archived static releases, currently pinned to the 2016-10 release
    linked from DBpedia's `wiki archive
    <https://downloads.dbpedia.org/wiki-archive/dbpedia-version-2016-10.html>`_.
    Stable URLs, one uniform layout for every language. This is the default.
    The trade-off is data vintage: the categories are a snapshot of Wikipedia
    as of 2016, not of today.

``databus``
    DBpedia's current distribution channel, which resolves versioned artifacts
    through an API instead of fixed paths. Not implemented yet.
"""

WIKI_ARCHIVE = 'wiki-archive'
DATABUS = 'databus'

#: Every engine name fastcat recognises, implemented or not.
available_engines = (WIKI_ARCHIVE, DATABUS)

#: The engines that can actually download something today.
implemented_engines = (WIKI_ARCHIVE,)

DEFAULT_ENGINE = WIKI_ARCHIVE

#: Archived release the wiki-archive engine is pinned to.
WIKI_ARCHIVE_RELEASE = '2016-10'

WIKI_ARCHIVE_URL_PATTERN = (
    'https://downloads.dbpedia.org/{release}/core-i18n/{mapping}/'
    'skos_categories_{mapping}.ttl.bz2'
)


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


def skos_url(wikipedia_mapping, engine=DEFAULT_ENGINE):
    """Build the download URL of a language's SKOS categories dump.

    Args:
        wikipedia_mapping (str): DBpedia subdomain for the language, i.e. the
            ``wikipedia_mapping`` of a :mod:`fastcat.lang` entry. Note this is
            not always the same as the language id -- Ukrainian is ``ua`` but
            lives under ``uk``.
        engine (:obj:`str`, optional): Which source to build the URL for.

    Returns:
        str: A direct download URL.
    """
    validate_engine(engine)

    return WIKI_ARCHIVE_URL_PATTERN.format(
        release=WIKI_ARCHIVE_RELEASE, mapping=wikipedia_mapping)
