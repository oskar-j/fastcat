"""The language -> Redis db mapping.

It is pickled to ``redis_ids.pickle`` in fastcat's data directory (see
:mod:`fastcat.paths`).
"""

import os
import pickle

import pycountry

import fastcat.lang as lang
import fastcat.paths as paths

SETTINGS_NAME = 'redis_ids.pickle'

#: Redis has 16 dbs, numbered 0 to 15, unless it is configured otherwise.
REDIS_DBS = 16

languages = dict()


def settings_file():
    """Where the mapping is kept."""
    return os.path.join(paths.data_dir(), SETTINGS_NAME)


# When creating new FastCat instance, try to unpickle configuration object
def load_settings():
    """Read the mapping. Without one, English is on db 0 and that's all."""
    # Always use the global 'languages' singleton dictionary
    global languages

    current = _read(settings_file())
    languages = current if current is not None else {'en': 0}


def _read(path):
    try:
        with open(path, 'rb') as handle:
            return pickle.load(handle)
    except (FileNotFoundError, NotADirectoryError):
        # Usually when file does not exist, i.e. FastCat ran for the first time
        return None
    except Exception:
        print('Unknown exception thrown while unpickling {} file'.format(path))
        raise


def _write(mapping):
    """Save ``mapping`` as the mapping, all of it or nothing.

    Raises:
        RuntimeError: The data directory cannot be written to.
    """
    directory = paths.ensure_data_dir()
    path = os.path.join(directory, SETTINGS_NAME)
    partial = paths.partial_name(path)

    try:
        with open(partial, 'xb') as handle:
            pickle.dump(mapping, handle)

        os.replace(partial, path)

    except OSError as exc:
        raise paths.unwritable(directory, exc) from exc

    finally:
        paths.discard(partial)


def save_settings(new_key):
    """Give language ``new_key`` the next free db, and save the mapping.

    Raises:
        ValueError: ``new_key`` is not a supported language id.
        RuntimeError: Every Redis db is taken already, or the data directory
            cannot be written to. The language is then left without a db.
    """
    # A slot handed out here is pickled and kept for good, so anything but a
    # real language id (an unrecognised code used to arrive here as None)
    # would hold a Redis db forever.
    if new_key not in {language.id for language in lang.available_languages.values()}:
        raise ValueError('Not a supported language id: {!r}'.format(new_key))

    new_value = _get_next_slot()

    if new_value >= REDIS_DBS:
        # Redis would answer the first command on it with "ERR DB index is
        # out of range"
        raise RuntimeError(
            'Redis has {} dbs, numbered 0 to {}, and the language -> Redis db mapping '
            'in {} gives out the last of them, so there is none left for {!r}.'.format(
                REDIS_DBS, REDIS_DBS - 1, settings_file(), new_key))

    # Saved first, so a failed write leaves the slot unassigned
    _write(dict(languages, **{new_key: new_value}))

    print('Assigning redis id {} to language {}'.format(new_value, new_key))

    languages[new_key] = new_value
    return new_value


def _get_next_slot():
    return max(languages.values()) + 1


def language_info(key):
    """pycountry's language record for a fastcat language id, or None.

    Looked up by the language's ISO 639-1 code, which is its DBpedia code
    (``wikipedia_mapping``) and not always its fastcat id: Ukrainian is
    ``ua`` in fastcat, Ukraine's country code, but ``uk`` in ISO 639-1. The
    lookup by id used to fall back to pycountry's countries for that, and
    reported Ukraine (#30).
    """
    codes = [language.wikipedia_mapping for language in lang.available_languages.values()
             if language.id == key] + [key]

    for code in codes:
        result = pycountry.languages.get(alpha_2=code)

        if result is not None:
            return result

    return None


def get_language_id(slot):
    """The fastcat language id a db slot is assigned to, or None."""
    for key, value in languages.items():
        if value == slot:
            return key
    return None


def get_language(slot):
    key = get_language_id(slot)
    if key is None:
        return None
    return language_info(key)


def get_slot(language):
    if language not in languages:
        raise ValueError
    return languages[language]
