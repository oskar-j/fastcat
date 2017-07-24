def normalize_language(lang):
    language_normalized = lang.lower().replace('_', '-')
    if language_normalized in ['en', 'en-uk', 'en-us', 'us-us', 'uk-uk']:
        return 'en'
    if language_normalized in ['pt', 'pt-pt', 'pt-br']:
        return 'pt'
    return
