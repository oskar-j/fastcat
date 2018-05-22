from collections import namedtuple


Language = namedtuple('Language', ['id', 'locales', 'alternate'])


available_languages = {'English': Language(id='en', locales=['en-gb', 'en-us', 'en-ca', 'en-nz'], alternate='eng'),
                       'Portuguese': Language(id='pt', locales=['pt-pt', 'pt-br'], alternate='por'),
                       'Japanese': Language(id='ja', locales=['ja-jp'], alternate='jpn'),
                       'Polish': Language(id='pl', locales=['pl-pl'], alternate='pol')}
