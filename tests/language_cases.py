"""Known-good category relations used by the integration tests.

One broader/narrower pair per supported language. ``narrower_of`` is a category
whose *narrower* set contains ``expected_narrower``, and likewise for the
broader direction -- they are not always the same category.
"""

from collections import namedtuple

LanguageCase = namedtuple(
    'LanguageCase',
    ['language', 'broader_of', 'expected_broader', 'narrower_of', 'expected_narrower'],
)

LANGUAGE_CASES = [
    LanguageCase('en', 'Computer programming', 'Software engineering',
                 'Functional programming', 'Functional languages'),
    LanguageCase('cs', 'Pivovary', 'Pivo',
                 'Průmyslové stavby', 'Pivovary'),
    LanguageCase('de', 'Nikola Tesla als Namensgeber', 'Nikola Tesla',
                 'Wissenschaftler als Thema', 'Nikola Tesla'),
    LanguageCase('et', 'Tallinn', 'Eesti linnad',
                 'Tallinn', 'Tallinna geograafia'),
    LanguageCase('ja', '日本の都道府県', '日本の行政区画',
                 '日本の都道府県', '都道府県庁'),
    LanguageCase('pl', 'Husaria', 'Jeździectwo',
                 'Jeździectwo', 'Husaria'),
    LanguageCase('pt', 'Placas de som', 'Hardware',
                 'Hardware', 'Computadores'),
    LanguageCase('ru', 'Русские супы', 'Русская кухня',
                 'Русские супы', 'Борщ'),
    LanguageCase('ua', 'Київська Русь', 'Київщина',
                 'Київська Русь', 'Київське князівство'),
]
