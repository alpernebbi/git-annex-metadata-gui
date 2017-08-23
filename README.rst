======================
Git-Annex-Metadata-Gui
======================
A graphical interface to the metadata functionality of git-annex_.

.. _git-annex: https://git-annex.branchable.com/

Requirements
------------
- Python 3
- git-annex-adapter_
- PyQt5

.. _git-annex-adapter: https://github.com/alpernebbi/git-annex-adapter

Usage
-----
::

    usage: git-annex-metadata-gui [option ...] [repo-path]

    A graphical interface for git-annex metadata.

    positional arguments:
      repo-path      path of the git-annex repository

    optional arguments:
      -h, --help     show this help message and exit
      -v, --version  print version information and exit
      --debug        print debug-level log messages
      --full-load    don't load models incrementially

    Also see the manual entry for qt5options(7)

Screenshots
-----------

.. image:: https://github.com/alpernebbi/
    git-annex-metadata-gui/wiki/screenshots/v020s1.png
    :alt: Workflow with a maximized window, both docks visible.

See `the wiki page`_ for more screenshots.

.. _the wiki page: https://github.com/alpernebbi/
    git-annex-metadata-gui/wiki/Screenshots
