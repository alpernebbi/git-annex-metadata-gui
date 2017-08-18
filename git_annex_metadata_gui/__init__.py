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

import sys
import logging

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from .utils import StatusBarLogHandler
from .main_window import MainWindow

app = None

def main():
    global app
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)

    statusbar_handler = StatusBarLogHandler(main_window.statusBar())
    statusbar_handler.setLevel(logging.INFO)

    logger = logging.getLogger()
    logger.addHandler(stderr_handler)
    logger.addHandler(statusbar_handler)
    logger.setLevel(logging.INFO)

    main_window.show()
    return app.exec_()

if __name__ == "__main__":
    main()
