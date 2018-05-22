import pickle
import os
import sys
import pycountry


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
            return pycountry.languages.get(alpha_2=key)


def get_slot(language):
    if language not in languages:
        raise ValueError
    return languages[language]
