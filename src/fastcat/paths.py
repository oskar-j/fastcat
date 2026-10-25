"""Where fastcat keeps its files: the downloaded dumps and the language ->
Redis db mapping.

That is the user's cache directory, unless ``FASTCAT_DATA_DIR`` says
otherwise. Nothing is created until a file has to be written there. Up to
0.3.5 the files lived inside the installed package, and importing fastcat
created the directories, which failed on a read-only install (#33).
"""

import os
import shutil
import sys
import uuid

#: The environment variable that overrides where fastcat keeps its files.
DATA_DIR_VARIABLE = 'FASTCAT_DATA_DIR'

#: The package directory. Up to 0.3.5, dumps were cached in ``data/`` and the
#: mapping in ``settings/`` here; :class:`fastcat.FastCat` moves them out.
LEGACY_DIR = os.path.dirname(os.path.realpath(__file__))


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


def remove_quietly(path):
    """Remove a file or an empty directory if possible, and never raise.

    For files that are no longer needed but may sit somewhere read-only.
    """
    try:
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)
    except OSError:
        pass


def same_filesystem(path, other):
    """Whether two existing paths are on the same filesystem."""
    try:
        return os.stat(path).st_dev == os.stat(other).st_dev
    except OSError:
        return False


def copy(source, destination):
    """Copy a file, never leaving part of it at ``destination``.

    Raises:
        OSError: ``source`` cannot be read or ``destination`` written.
    """
    partial = partial_name(destination)

    try:
        shutil.copyfile(source, partial)
        os.replace(partial, destination)
    finally:
        discard(partial)


def move(source, destination):
    """Move a file on the same filesystem.

    If it cannot be renamed, as in a read-only directory, it is copied, and
    ``source`` is left in place unless it can be removed.

    Raises:
        OSError: ``source`` cannot be read or ``destination`` written.
    """
    try:
        os.replace(source, destination)
        return
    except OSError:
        pass

    copy(source, destination)
    remove_quietly(source)


def kept_on_another_filesystem():
    """Why files were copied, not moved, out of the package directory."""
    return ('The originals stay where they are, since they are on another '
            'filesystem. To keep fastcat\'s files on a volume, point {} at '
            'it.'.format(DATA_DIR_VARIABLE))
