"""The language -> Redis db mapping.

It is pickled to ``redis_ids.pickle`` in fastcat's data directory (see
:mod:`fastcat.paths`). Up to 0.3.5 it lived inside the installed package;
:func:`load_settings` moves it out.
"""

import os
import pickle
import warnings

import pycountry

import fastcat.lang as lang
import fastcat.paths as paths

SETTINGS_NAME = 'redis_ids.pickle'

languages = dict()


def settings_file():
    """Where the mapping is kept."""
    return os.path.join(paths.data_dir(), SETTINGS_NAME)


def legacy_settings_file():
    """Where fastcat 0.3.5 and earlier kept the mapping, inside the package."""
    return os.path.join(paths.LEGACY_DIR, 'settings', SETTINGS_NAME)


# When creating new FastCat instance, try to unpickle configuration object
def load_settings():
    """Read the mapping. Without one, English is on db 0 and that's all.

    A mapping that fastcat 0.3.5 or earlier left inside the package is moved
    to the data directory. If one is there already, the two are merged; if
    they give a db to different languages, the old one is left where it is,
    with a warning.
    """
    # Always use the global 'languages' singleton dictionary
    global languages

    current = _read(settings_file())
    legacy = _read(legacy_settings_file())

    if legacy is not None:
        current = _adopt(legacy, current)

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


def _adopt(legacy, current):
    """Move the legacy mapping into the data directory.

    Returns:
        dict: The mapping to use from now on.
    """
    old, new = legacy_settings_file(), settings_file()
    merged = legacy if current is None else _merge(current, legacy)

    if merged is None:
        warnings.warn(
            'fastcat found two language -> Redis db mappings that disagree: {} '
            '(from fastcat 0.3.5 or earlier, in this environment) gives {}, and '
            '{} (used from now on) gives {}. If this environment\'s Redis was '
            'loaded by the old one, copy it over the new one. Either way, delete '
            'the old one to stop this warning.'.format(
                old, _describe(legacy), new, _describe(current)),
            RuntimeWarning, stacklevel=4)
        return current

    if merged != current:
        try:
            _write(merged)
        except RuntimeError as exc:
            warnings.warn(
                'Could not move the language -> Redis db mapping out of {}: {} '
                'It is used from there for now.'.format(old, exc),
                RuntimeWarning, stacklevel=4)
            return merged

    # On another filesystem the old one may be on a volume that outlasts the
    # new one, as with docker-compose.yml up to 0.3.5, so it is left there
    moving = paths.same_filesystem(old, paths.data_dir())

    if merged != current:
        if moving:
            print('Moved the language -> Redis db mapping from {} to {}'.format(old, new))
        else:
            print('Copied the language -> Redis db mapping from {} to {}. {}'.format(
                old, new, paths.kept_on_another_filesystem()))

    if moving:
        paths.remove_quietly(old)

    return merged


def _merge(current, legacy):
    """``current`` plus ``legacy``'s languages, or None if they disagree.

    They disagree when they give one language two different dbs, or one db
    to two different languages.
    """
    merged = dict(current)

    for language, slot in legacy.items():
        owner = next((key for key, value in merged.items() if value == slot), None)

        if merged.get(language, slot) != slot or owner not in (None, language):
            return None

        merged[language] = slot

    return merged


def _describe(mapping):
    return ', '.join('{} db {}'.format(language, slot)
                     for language, slot in sorted(mapping.items(), key=lambda item: item[1]))


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
        RuntimeError: The data directory cannot be written to. The language
            is then left without a db.
    """
    # A slot handed out here is pickled and kept for good, so anything but a
    # real language id (an unrecognised code used to arrive here as None)
    # would hold a Redis db forever.
    if new_key not in {language.id for language in lang.available_languages.values()}:
        raise ValueError('Not a supported language id: {!r}'.format(new_key))

    new_value = _get_next_slot()

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
