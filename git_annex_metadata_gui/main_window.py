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

from PyQt5 import QtCore
from PyQt5 import QtWidgets

from git_annex_adapter.repo import GitAnnexRepo

from .models import AnnexedKeyMetadataModel
from .models import AnnexedFileMetadataModel
from .main_window_ui import Ui_MainWindow


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi()

        self.repo = None
        self.model_keys = AnnexedKeyMetadataModel(self)
        proxy_keys = QtCore.QSortFilterProxyModel(self.view_keys)
        proxy_keys.setSourceModel(self.model_keys)
        self.view_keys.setModel(proxy_keys)

        self.model_head = AnnexedFileMetadataModel(self.view_head)
        self.model_head.setSourceModel(self.model_keys)
        proxy_head = QtCore.QSortFilterProxyModel(self.view_head)
        proxy_head.setSourceModel(self.model_head)
        self.view_head.setModel(proxy_head)

    def setupUi(self, window=None):
        if window is None:
            window = self
        super().setupUi(window)

    def retranslateUi(self, window=None):
        if window is None:
            window = self
        super().retranslateUi(window)

    @QtCore.pyqtSlot()
    def open_repo(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self)
        if path:
            self.repo = GitAnnexRepo(path)
            self.refresh_repo()

    @QtCore.pyqtSlot()
    def refresh_repo(self):
        if self.repo:
            self.model_keys.setRepo(self.repo)

