DISTNAME = 'fastcat'
DESCRIPTION = 'Navigate Wikipedia categories quickly in a local redis instance'
AUTHOR = 'Ed Summers'
AUTHOR_EMAIL = 'ehs@pobox.com'
MAINTAINER = 'Oskar Jarczyk'
MAINTAINER_EMAIL = 'oskar.jarczyk@gmail.com'
LICENSE = 'CC BY-SA 3.0'
URL = 'https://github.com/oskar-j/fastcat'
VERSION = '0.1.2'
DOWNLOAD_URL = 'https://github.com/oskar-j/fastcat/archive/v_01_2.tar.gz'
KEYWORDS = ['Wikipedia', 'categories', 'wiki-api', 'knowledge engineering']
CLASSIFIERS = ['Development Status :: 3 - Alpha',
               'Intended Audience :: Science/Research',
               'Topic :: Scientific/Engineering :: Artificial Intelligence',
               'License :: OSI Approved',
               'Programming Language :: Python :: 3',
               'Programming Language :: Python :: 3.5',
               'Programming Language :: Python :: 3.6',
               'Programming Language :: Python :: 3.7',
               ]


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
        download_url=DOWNLOAD_URL,
        packages=find_packages(exclude=['*tests*']),
        install_requires=['redis', 'pycountry'])

    setup(**metadata)


if __name__ == '__main__':
    setup_package()
