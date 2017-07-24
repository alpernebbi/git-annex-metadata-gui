#!/usr/bin/env python3

# Git-Annex-Metadata-Gui
# Copyright (C) 2017 Alper Nebi Yasak
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import codecs
import setuptools

root = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(root, 'README.rst'), encoding='utf-8') as f:
    readme = f.read()

setuptools.setup(
    name='git-annex-metadata-gui',
    version='0.2.0',
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
            'git-annex-metadata-gui=git_annex_metadata_gui:main',
        ],
    },
    keywords='git-annex metadata',
    packages=['git_annex_metadata_gui'],
    install_requires=['PyQt5', 'git-annex-adapter>=0.2.0'],
)
