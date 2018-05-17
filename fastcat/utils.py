def normalize_language(lang):
    language_normalized = lang.lower().replace('_', '-')

    # ISO 639-1 code for English
    if language_normalized in ['en', 'en-gb', 'en-us', 'en-ca', 'en-nz']:
        return 'en'

    # ISO 639-2
    if language_normalized == 'eng':
        return 'en'

    # ISO 639-1 code for Portuguese
    if language_normalized in ['pt', 'pt-pt', 'pt-br']:
        return 'pt'

    # ISO 639-2
    if language_normalized == 'por':
        return 'pt'

    # ISO 639-1 code for Japanese
    if language_normalized in ['ja', 'ja-jp']:
        return 'ja'

    # ISO 639-2
    if language_normalized == 'jpn':
        return 'ja'

    return


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
