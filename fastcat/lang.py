from collections import namedtuple

Language = namedtuple('Language', ['id', 'locales', 'alternate'])

available_languages = {'English': Language(id='en', locales=['en-gb', 'en-us', 'en-ca', 'en-nz'], alternate='eng'),
                       'German': Language(id='de', locales=['de-de'], alternate='ger'),
                       'Japanese': Language(id='ja', locales=['ja-jp'], alternate='jpn'),
                       'Polish': Language(id='pl', locales=['pl-pl'], alternate='pol'),
                       'Portuguese': Language(id='pt', locales=['pt-pt', 'pt-br'], alternate='por')}
