from distutils.core import setup

setup(
  name='fastcat',
  packages=['fastcat'],  # this must be the same as the name above
  version='0.1',
  description='Navigate wikipedia categories quickly in a local redis instance',
  author='Oskar Jarczyk',
  author_email='oskar.jarczyk@gmail.com',
  url='https://github.com/oskar-j/fastcat',  # use the URL to the github repo
  download_url='https://github.com/oskar-j/fastcat/archive/0.1.tar.gz',  # I'll explain this in a second
  keywords=['wikipedia', 'categories', 'wiki-api', 'knowledge engineering'],  # arbitrary keywords
  classifiers=[],
)
