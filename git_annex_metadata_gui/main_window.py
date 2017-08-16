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

import functools

from PyQt5 import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from git_annex_adapter.repo import GitAnnexRepo

from .models import AnnexedKeyMetadataModel
from .models import AnnexedFileMetadataModel
from .main_window_ui import Ui_MainWindow
from .metadata_edit import MetadataEdit


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi()

        self.repo = None
        self.model_keys = AnnexedKeyMetadataModel(self)
        self.view_keys.setModel(self.model_keys)

        self.model_head = AnnexedFileMetadataModel(self.view_head)
        self.model_head.setSourceModel(self.model_keys)
        self.view_head.setModel(self.model_head)

        self.model_keys.headerDataChanged.connect(self.refresh_headers)

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
            self.stack_preview.clear()
            self.metadata_edit.clear()

    @QtCore.pyqtSlot()
    def refresh_headers(self):
        headers = self.model_keys.fields[1:]
        self.menu_headers.clear()

        header = self.view_keys.horizontalHeader()

        def on_triggered(h):
            def set_visibility(visible):
                self.view_keys.show_header(h, visible)
                self.view_head.show_header(h, visible)
            return set_visibility

        def on_visibility_set(action, h):
            def set_checked(h_, visible):
                if h == h_:
                    action.setChecked(visible)
            return set_checked

        for idx, h in enumerate(headers, 1):
            hidden = header.isSectionHidden(idx)

            action = QtWidgets.QAction(self)
            action.setText(h)
            action.setCheckable(True)
            action.setChecked(not hidden)
            action.triggered.connect(on_triggered(h))

            signal = self.view_keys.header_visibility_changed
            signal.connect(on_visibility_set(action, h))

            self.menu_headers.addAction(action)

        empty = not headers
        self.menu_headers.setDisabled(empty)

