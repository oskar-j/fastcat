from collections import namedtuple

#: A supported language.
#:
#: - ``id``: fastcat's code for it, ISO 639-1 except for Ukrainian (``ua``)
#: - ``locales``: locales that also select it, lower case
#: - ``alternate``: its ISO 639-2 code
#: - ``wikipedia_mapping``: its DBpedia code (``uk`` for Ukrainian)
#: - ``category_prefix``: how its Wikipedia names categories, as in
#:   ``Catégorie:Fromage``
Language = namedtuple('Language',
                      ['id', 'locales', 'alternate', 'wikipedia_mapping', 'category_prefix'])

available_languages = {'Czech': Language(id='cs', locales=['cs-cs'], alternate='cze',
                                         wikipedia_mapping='cs', category_prefix='Kategorie:'),
                       'Dutch': Language(id='nl', locales=['nl-nl', 'nl-be'], alternate='dut',
                                         wikipedia_mapping='nl', category_prefix='Categorie:'),
                       'English': Language(id='en', locales=['en-gb', 'en-us', 'en-ca', 'en-nz'],
                                           alternate='eng', wikipedia_mapping='en',
                                           category_prefix='Category:'),
                       'Estonian': Language(id='et', locales=['et-et'], alternate='est',
                                            wikipedia_mapping='et', category_prefix='Kategooria:'),
                       'Finnish': Language(id='fi', locales=['fi-fi'], alternate='fin',
                                           wikipedia_mapping='fi', category_prefix='Luokka:'),
                       'French': Language(id='fr', locales=['fr-fr', 'fr-be', 'fr-ca', 'fr-ch'],
                                          alternate='fre', wikipedia_mapping='fr',
                                          category_prefix='Catégorie:'),
                       'German': Language(id='de', locales=['de-de'], alternate='ger',
                                          wikipedia_mapping='de', category_prefix='Kategorie:'),
                       'Hungarian': Language(id='hu', locales=['hu-hu'], alternate='hun',
                                             wikipedia_mapping='hu', category_prefix='Kategória:'),
                       'Italian': Language(id='it', locales=['it-it', 'it-ch'], alternate='ita',
                                           wikipedia_mapping='it', category_prefix='Categoria:'),
                       'Japanese': Language(id='ja', locales=['ja-jp'], alternate='jpn',
                                            wikipedia_mapping='ja', category_prefix='Category:'),
                       'Polish': Language(id='pl', locales=['pl-pl'], alternate='pol',
                                          wikipedia_mapping='pl', category_prefix='Kategoria:'),
                       'Portuguese': Language(id='pt', locales=['pt-pt', 'pt-br'], alternate='por',
                                              wikipedia_mapping='pt', category_prefix='Categoria:'),
                       'Russian': Language(id='ru', locales=['ru-ru'], alternate='rus',
                                           wikipedia_mapping='ru', category_prefix='Категория:'),
                       'Spanish': Language(id='es', locales=['es-es', 'es-mx', 'es-ar', 'es-us'],
                                           alternate='spa', wikipedia_mapping='es',
                                           category_prefix='Categoría:'),
                       'Swedish': Language(id='sv', locales=['sv-se', 'sv-fi'], alternate='swe',
                                           wikipedia_mapping='sv', category_prefix='Kategori:'),
                       'Ukrainian': Language(id='ua', locales=['ua-ua', 'uk-ua'], alternate='ukr',
                                             wikipedia_mapping='uk', category_prefix='Категорія:')}


def category_uri_prefix(language):
    """What DBpedia's resource URI for one of ``language``'s categories starts
    with, such as ``http://fr.dbpedia.org/resource/Catégorie:``.

    English is the one edition without a subdomain of its own.
    """
    host = 'dbpedia.org' if language.wikipedia_mapping == 'en' else (
        '{}.dbpedia.org'.format(language.wikipedia_mapping))

    return 'http://{}/resource/{}'.format(host, language.category_prefix)
