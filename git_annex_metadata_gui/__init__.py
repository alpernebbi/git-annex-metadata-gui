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

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from .utils import StatusBarLogHandler
from .main_window import MainWindow

app = None
my_args = None
qt_args = None

logger = logging.getLogger(__name__)

def main():
    prog, *args = sys.argv

    global my_args, qt_args
    my_args, remaining = parse_args(args)
    qt_args = [prog] + remaining

    global app
    app = QtWidgets.QApplication(qt_args)
    main_window = MainWindow()
    setup_logger(main_window, debug=my_args.debug)

    main_window.show()
    return app.exec_()


def setup_logger(main_window, debug=False):
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)

    statusbar_handler = StatusBarLogHandler(main_window.statusBar())
    statusbar_handler.setLevel(logging.INFO)

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


def parse_args(args):
    parser = argparse.ArgumentParser(
        description="A graphical interface for git-annex metadata.",
        usage="%(prog)s [option ...]",
        epilog="Also see the manual entry for qt5options(7)",
        add_help=True,
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

    namespace, remaining = parser.parse_known_args()
    return namespace, remaining


if __name__ == "__main__":
    main()
