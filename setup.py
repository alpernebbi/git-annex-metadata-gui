#!/usr/bin/env python3

import os
import codecs
import setuptools

root = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(root, 'README.rst'), encoding='utf-8') as f:
    readme = f.read()

setuptools.setup(
    name='git-annex-metadata-gui',
    version='0.1.0',
    description='Graphical interface for git-annex metadata commands',
    long_description=readme,
    url='https://github.com/alpernebbi/git-annex-metadata-gui',
    author='Alper Nebi Yasak',
    author_email='alpernebiyasak@gmail.com',
    license='GPL3+',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Utilities',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    entry_points={
        'gui_scripts': [
            'git-annex-metadata-gui=git_annex_metadata_gui.gui:main',
        ],
    },
    keywords='git-annex metadata',
    packages=['git_annex_metadata_gui'],
    install_requires=['PyQt5', 'git-annex-adapter'],
)