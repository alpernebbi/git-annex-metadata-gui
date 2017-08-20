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

import argparse
import sys
import logging

from PyQt5 import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from . import utils
from .utils import StatusBarLogHandler
from .main_window import MainWindow

app = None

logger = logging.getLogger(__name__)

def main():
    global app
    app = QtWidgets.QApplication(sys.argv)
    my_args = parse_args(app.arguments())

    main_window = MainWindow()
    setup_logger(main_window, debug=my_args.debug)

    if my_args.full_load:
        utils.autoconsume_timeout = float('inf')

    if my_args.repo_path:
        QtCore.QMetaObject.invokeMethod(
            main_window, 'open_repo',
            Qt.Qt.QueuedConnection,
            QtCore.Q_ARG(str, my_args.repo_path),
        )

    main_window.show()
    return app.exec_()


def setup_logger(main_window, debug=False):
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)

    stderr_formatter = logging.Formatter(
        fmt='[{asctime}] [{name}] [{levelname}]: {message}',
        style='{',
    )
    stderr_handler.setFormatter(stderr_formatter)

    statusbar_handler = StatusBarLogHandler(main_window.statusBar())
    statusbar_handler.setLevel(logging.INFO)
    statusbar_formatter = logging.Formatter(
        fmt='{message}',
        style='{',
    )
    statusbar_handler.setFormatter(statusbar_formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(stderr_handler)
    root_logger.addHandler(statusbar_handler)
    root_logger.setLevel(logging.INFO)

    if debug:
        stderr_handler.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.DEBUG)
        logger.debug('Enabled debug messages')

    def excepthook(exc_type, value, traceback):
        exc_info = (exc_type, value, traceback)
        logger.critical('%s', value, exc_info=exc_info)
    sys.excepthook = excepthook


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="A graphical interface for git-annex metadata.",
        usage="%(prog)s [option ...] [repo-path]",
        epilog="Also see the manual entry for qt5options(7)",
        add_help=True,
    )

    parser.add_argument(
        "repo_path",
        metavar='repo-path',
        nargs='?',
        help="path of the git-annex repository",
    )

    parser.add_argument(
        "--version", "-v",
        action='version',
        version="%(prog)s v0.2.0",
        help="print version information and exit",
    )

    parser.add_argument(
        "--debug",
        action='store_true',
        help="print debug-level log messages",
    )

    parser.add_argument(
        "--full-load",
        action='store_true',
        help="don't load models incrementially",
    )

    return parser.parse_args(argv[1:])


if __name__ == "__main__":
    main()
