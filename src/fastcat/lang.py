from collections import namedtuple

Language = namedtuple('Language', ['id', 'locales', 'alternate', 'wikipedia_mapping'])

available_languages = {'Czech': Language(id='cs', locales=['cs-cs'],
                                         alternate='cze', wikipedia_mapping='cs'),
                       'English': Language(id='en', locales=['en-gb', 'en-us', 'en-ca', 'en-nz'],
                                           alternate='eng', wikipedia_mapping='en'),
                       'Estonian': Language(id='et', locales=['et-et'],
                                            alternate='est', wikipedia_mapping='et'),
                       'German': Language(id='de', locales=['de-de'],
                                          alternate='ger', wikipedia_mapping='de'),
                       'Japanese': Language(id='ja', locales=['ja-jp'],
                                            alternate='jpn', wikipedia_mapping='ja'),
                       'Polish': Language(id='pl', locales=['pl-pl'],
                                          alternate='pol', wikipedia_mapping='pl'),
                       'Portuguese': Language(id='pt', locales=['pt-pt', 'pt-br'],
                                              alternate='por', wikipedia_mapping='pt'),
                       'Russian': Language(id='ru', locales=['ru-ru'],
                                           alternate='rus', wikipedia_mapping='ru'),
                       'Ukrainian': Language(id='ua', locales=['ua-ua'],
                                             alternate='ukr', wikipedia_mapping='uk')}
