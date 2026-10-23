import fastcat.lang as languages


def normalize_language(lang):
    language_normalized = lang.lower().replace('_', '-')

    for l in languages.available_languages.values():
        if l.id == language_normalized:
            # ISO 639-1
            return l.id
        elif language_normalized in l.locales:
            # id and locale pair
            return l.id
        elif language_normalized == l.alternate:
            # ISO 639-2
            return l.id
        elif language_normalized == l.wikipedia_mapping:
            # DBpedia's code, which is not always the id: Ukrainian is 'ua'
            # in fastcat but 'uk' on DBpedia (and in ISO 639-1)
            return l.id

    return None


def supported_language_ids():
    return sorted(l.id for l in languages.available_languages.values())


def resolve_language(lang):
    """Normalise a language code, raising if fastcat does not support it.

    Unlike :func:`normalize_language`, which returns None for unknown input,
    this is meant for user-facing entry points, which must fail before an
    unknown language reaches the slot store or Redis.

    Raises:
        ValueError: ``lang`` is not a supported language in any of its forms.
    """
    normalized = normalize_language(lang)

    if normalized is None:
        raise ValueError(
            'Unsupported language {!r}. Supported languages: {}, or their '
            'ISO 639-2 codes and locales such as \'ger\' or \'pt-BR\'.'.format(
                lang, ', '.join(supported_language_ids())))

    return normalized


def get_wikipedia_mapping(normalized_lang):
    for l in languages.available_languages.values():
        if l.id == normalized_lang:
            return l.wikipedia_mapping


# Print iterations progress
def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='#'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()
