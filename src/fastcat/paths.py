"""Where fastcat keeps its files: the downloaded dumps and the language ->
Redis db mapping.

That is the user's cache directory, unless ``FASTCAT_DATA_DIR`` says
otherwise. Nothing is created until a file has to be written there. Up to
0.3.5 the files lived inside the installed package, and importing fastcat
created the directories, which failed on a read-only install (#33).
"""

import fnmatch
import os
import sys
import uuid

#: The environment variable that overrides where fastcat keeps its files.
DATA_DIR_VARIABLE = 'FASTCAT_DATA_DIR'

#: The package directory. Up to 0.3.5, dumps were cached in ``data/`` and the
#: mapping in ``settings/`` here. 0.3.6 moved them to the data directory, and
#: fastcat now only warns about any that are left (see :func:`legacy_files`).
LEGACY_DIR = os.path.dirname(os.path.realpath(__file__))

#: Where in :data:`LEGACY_DIR` 0.3.5 and earlier kept the mapping.
LEGACY_SETTINGS = os.path.join('settings', 'redis_ids.pickle')


def data_dir():
    """The directory fastcat keeps its dumps and its mapping in.

    ``FASTCAT_DATA_DIR`` if that is set, otherwise the user's cache directory
    (see :func:`default_data_dir`). The variable is read on every call, so
    setting it from code works too. The directory may not exist yet.
    """
    override = os.environ.get(DATA_DIR_VARIABLE)

    if override:
        return os.path.abspath(os.path.expanduser(override))

    return default_data_dir()


def default_data_dir(platform=sys.platform, environ=None, home=None):
    """The user's cache directory for fastcat on ``platform``.

    ``~/.cache/fastcat`` (or ``$XDG_CACHE_HOME/fastcat``) on Linux,
    ``~/Library/Caches/fastcat`` on macOS and ``%LOCALAPPDATA%\\fastcat\\Cache``
    on Windows, which is where ``platformdirs`` puts them too.
    """
    environ = os.environ if environ is None else environ
    home = home or os.path.expanduser('~')

    if platform == 'win32':
        base = environ.get('LOCALAPPDATA') or os.path.join(home, 'AppData', 'Local')
        return os.path.join(base, 'fastcat', 'Cache')

    if platform == 'darwin':
        return os.path.join(home, 'Library', 'Caches', 'fastcat')

    # The XDG spec says to ignore a relative path
    base = environ.get('XDG_CACHE_HOME', '')

    if not os.path.isabs(base):
        base = os.path.join(home, '.cache')

    return os.path.join(base, 'fastcat')


def ensure_data_dir():
    """Create the data directory if need be, and return its path.

    Raises:
        RuntimeError: The directory cannot be created.
    """
    directory = data_dir()

    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as exc:
        raise unwritable(directory, exc) from exc

    return directory


def unwritable(directory, exc):
    """The error to raise when fastcat cannot write to ``directory``."""
    return RuntimeError(
        'fastcat cannot write to its data directory {} ({}). Point the {} '
        'environment variable at a directory you can write to.'.format(
            directory, exc, DATA_DIR_VARIABLE))


def legacy_files():
    """The files fastcat 0.3.5 and earlier left in the package directory.

    Returns:
        list: Their paths relative to :data:`LEGACY_DIR`, such as
        ``settings/redis_ids.pickle`` and ``data/skos-wiki-archive-en.nt.bz2``.
    """
    found = []

    if os.path.isfile(os.path.join(LEGACY_DIR, LEGACY_SETTINGS)):
        found.append(LEGACY_SETTINGS)

    try:
        names = os.listdir(os.path.join(LEGACY_DIR, 'data'))
    except OSError:
        names = []

    found += [os.path.join('data', name) for name in sorted(names)
              if fnmatch.fnmatch(name, 'skos-*.nt.bz2')]
    return found


def partial_name(path):
    """A temporary name next to ``path``, for a file that is being written.

    The random part keeps two processes writing the same file out of each
    other's way.
    """
    return '{}.{}.part'.format(path, uuid.uuid4().hex[:12])


def discard(path):
    """Remove a file if it is there."""
    if os.path.isfile(path):
        os.remove(path)
