from setuptools import setup

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except ImportError:
    long_description = ('Gits is a web-based terminal emulator. Gits consists '
                        'of two parts: a client and a server. Note that the '
                        'package provides the server.')


setup(name='gits',
      version='0.4',
      description='Gits package',
      long_description=long_description,
      url='https://github.com/tolstoyevsky/gits.git',
      maintainer='Evgeny Golyshev',
      maintainer_email='Evgeny Golyshev <eugulixes@gmail.com>',
      license='http://www.apache.org/licenses/LICENSE-2.0',
      scripts=['bin/server.py'],
      packages=['gits'],
      package_data={'gits': ['linux_console.yml']},
      install_requires=[
          'PyYAML',
          'tornado',
      ])
