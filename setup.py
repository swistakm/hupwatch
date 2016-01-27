# -*- coding: utf-8 -*-
from setuptools import setup
import os


def get_version(version_tuple):
    if not isinstance(version_tuple[-1], int):
        return '.'.join(map(str, version_tuple[:-1])) + version_tuple[-1]
    return '.'.join(map(str, version_tuple))


init = os.path.join(os.path.dirname(__file__), 'hupwatch', '__init__.py')
version_line = list(filter(lambda l: l.startswith('VERSION'), open(init)))[0]
VERSION = get_version(eval(version_line.split('=')[-1]))

INSTALL_REQUIRES = []

try:
    from pypandoc import convert

    def read_md(f):
        return convert(f, 'rst')

except ImportError:
    print(
        "warning: pypandoc module not found, could not convert Markdown to RST"
    )

    def read_md(f):
        return open(f, 'r').read()  # noqa

README = os.path.join(os.path.dirname(__file__), 'README.md')

setup(
    name='hupwatch',
    version=VERSION,
    author='Michał Jaworski',
    author_email='swistakm@gmail.com',
    description='Simple process supervision agnostic utility for graceful reloading of services',  # noqa
    long_description=read_md(README),

    packages=['hupwatch'],

    url='https://github.com/swistakm/hupwatch',
    include_package_data=True,
    install_requires=[],
    zip_safe=False,

    license="BSD",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',

        'Operating System :: POSIX',

        'Topic :: System :: Systems Administration',

        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',

        'License :: OSI Approved :: BSD License',
    ],

    entry_points={
        'console_scripts': [
            'hupwatch = hupwatch.command:main'
        ]
    }
)
