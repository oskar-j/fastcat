DISTNAME = 'fastcat'
DESCRIPTION = 'Navigate Wikipedia categories quickly in a local redis instance'
AUTHOR = 'Ed Summers'
AUTHOR_EMAIL = 'ehs@pobox.com'
MAINTAINER = 'Oskar Jarczyk'
MAINTAINER_EMAIL = 'oskar.jarczyk@gmail.com'
LICENSE = 'CC BY-SA 3.0'
URL = 'https://github.com/oskar-j/fastcat'
VERSION = '0.1'
KEYWORDS = ['wikipedia', 'categories', 'wiki-api', 'knowledge engineering']
CLASSIFIERS = ['Development Status :: 3 - Alpha', ]


def setup_package():
    from setuptools import setup, find_packages

    metadata = dict(
        name=DISTNAME,
        description=DESCRIPTION,
        version=VERSION,
        classifiers=CLASSIFIERS,
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        maintainer=MAINTAINER,
        maintainer_email=MAINTAINER_EMAIL,
        license=LICENSE,
        url=URL,
        packages=find_packages(exclude=['*tests*']),
        install_requires=['redis'])

    setup(**metadata)


if __name__ == '__main__':
    setup_package()
