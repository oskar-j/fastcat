import pickle
import os
import sys
import pycountry
import fastcat.lang as lang


try:
    p = __file__
except NameError:
    p = sys.argv[0]

settings_filename = os.path.join(os.path.dirname(os.path.realpath(p)), 'settings', 'redis_ids.pickle')
languages = dict()


# When creating new FastCat instance, try to unpickle configuration object
def load_settings():
    # Always use the global 'languages' singleton dictionary
    global languages

    try:
        languages = pickle.load(open(settings_filename, "rb"))
    except FileNotFoundError:
        # Usually when file does not exist, i.e. FastCat ran for the first time
        languages = {'en': 0}
    except Exception as exc:
        print('Unknown exception thrown while unpickling {} file'.format(settings_filename))
        # TODO: investigate why PyPy fails and if there is some workaround
        raise exc


def save_settings(new_key):
    # A slot handed out here is pickled and kept for good, so anything but a
    # real language id (an unrecognised code used to arrive here as None)
    # would hold a Redis db forever.
    if new_key not in {language.id for language in lang.available_languages.values()}:
        raise ValueError('Not a supported language id: {!r}'.format(new_key))

    new_value = _get_next_slot()

    print('Assigning redis id {} to language {}'.format(new_value, new_key))

    languages[new_key] = new_value
    pickle.dump(languages, open(settings_filename, "wb"))
    return new_value


def _get_next_slot():
    return max(languages.values()) + 1


def get_language(slot):
    for key, value in languages.items():
        if value == slot:
            # normally this line below should work fine
            result = pycountry.languages.get(alpha_2=key)
            if result is None:
                # if not, below is last-chance workaround
                # due to some bugs in pycountry package
                result = [c for c in list(pycountry.countries) if c.alpha_2.lower() == key.lower()][0]
            return result


def get_slot(language):
    if language not in languages:
        raise ValueError
    return languages[language]
