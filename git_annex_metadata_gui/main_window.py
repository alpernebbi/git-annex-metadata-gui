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
import mimetypes

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
        proxy_keys = QtCore.QSortFilterProxyModel(self.view_keys)
        proxy_keys.setSourceModel(self.model_keys)
        self.view_keys.setModel(proxy_keys)

        self.model_head = AnnexedFileMetadataModel(self.view_head)
        self.model_head.setSourceModel(self.model_keys)
        proxy_head = QtCore.QSortFilterProxyModel(self.view_head)
        proxy_head.setSourceModel(self.model_head)
        self.view_head.setModel(proxy_head)

        self.model_keys.headerDataChanged.connect(self.refresh_headers)

        self.view_keys.selectionModel().selectionChanged.connect(
           self._on_selection_changed
        )
        self.view_head.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

        self.menu_docks.addAction(
            self.dock_preview.toggleViewAction()
        )
        self.menu_docks.addAction(
            self.dock_metadata.toggleViewAction()
        )

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
            self._clear_metadata_edit()

    @QtCore.pyqtSlot()
    def refresh_headers(self):
        headers = self.model_keys.fields[1:]
        self.menu_headers.clear()

        header = self.view_keys.horizontalHeader()

        for idx, h in enumerate(headers):
            hidden = header.isSectionHidden(idx + 1)

            action = QtWidgets.QAction(self)
            action.setText(h)
            action.setCheckable(True)
            action.setChecked(not hidden)
            action.triggered.connect(
                functools.partial(self.set_header_visible, h),
            )

            self.menu_headers.addAction(action)

        empty = not headers
        self.menu_headers.setDisabled(empty)

    @QtCore.pyqtSlot(str)
    def set_header_visible(self, header_title, visible=True):
        idx = self.model_keys.fields.index(header_title)
        header_keys = self.view_keys.horizontalHeader()
        header_keys.setSectionHidden(idx, not visible)
        header_head = self.view_head.header()
        header_head.setSectionHidden(idx, not visible)

    @QtCore.pyqtSlot(str)
    def set_header_hidden(self, header_title):
        self.set_header_visible(header_title, visible=False)

    @QtCore.pyqtSlot(str)
    def add_new_column(self, header_title):
        self.model_keys.insert_field(header_title)

    @QtCore.pyqtSlot()
    def clear_preview(self):
        self.text_preview.clear()

        old_scene = self.graphics_preview.scene()
        if old_scene:
            old_scene.clear()
            old_scene.deleteLater()

    @QtCore.pyqtSlot(str)
    def preview_text_file(self, path):
        page = self.page_text_preview
        self.stack_preview.setCurrentWidget(page)

        with open(path, 'r') as file:
            text = file.read()
        self.text_preview.setPlainText(text)

    @QtCore.pyqtSlot(str)
    def preview_image_file(self, path):
        page = self.page_graphics_preview
        self.stack_preview.setCurrentWidget(page)

        scene = QtWidgets.QGraphicsScene(self)
        self.graphics_preview.setScene(scene)

        # Using QImage instead of directly creating the QPixmap
        # prevents a segmentation fault in my container setup
        image = QtGui.QImage(path)
        if image.isNull():
            return

        pixmap = QtGui.QPixmap.fromImage(image)
        if pixmap.isNull():
            return

        pixmap_item = QtWidgets.QGraphicsPixmapItem(pixmap)
        scene.addItem(pixmap_item)
        self.graphics_preview.fitInView(
            pixmap_item,
            Qt.Qt.KeepAspectRatio,
        )

    def _on_selection_changed(self, selected, deselected):
        self.clear_preview()

        indexes = selected.indexes()
        if not indexes:
            return

        index = indexes[0]
        src_index = index.model().mapToSource(index)
        item = src_index.model().itemFromIndex(src_index)

        if self.dock_preview.isVisible():
            self._preview_item(item)
        if self.dock_metadata.isVisible():
            self._metadata_edit_item(item)

    def _preview_item(self, item):
        mime = self._mime_from_item(item)

        if not mime:
            return

        path = item.contentlocation

        if mime.startswith('text/'):
            self.preview_text_file(path)

        elif mime.startswith('image/'):
            self.preview_image_file(path)

    def _mime_from_item(self, item):
        try:
            path = item.contentlocation
        except AttributeError:
            return None
        if not path:
            return None

        try:
            name = item.name
        except AttributeError:
            name = None

        mime, encoding = None, None
        if name:
            mime, encoding = mimetypes.guess_type(name)
        if not mime:
            mime, encoding = mimetypes.guess_type(path)
        if encoding:
            return None

        return mime

    def _clear_metadata_edit(self):
        self._metadata_edit_item(None)

    def _metadata_edit_item(self, item):
        if item is not None and not hasattr(item, 'key'):
            return

        new_edit = MetadataEdit(
            parent=self.dock_metadata_contents,
            item=item,
        )

        layout = self.dock_metadata_contents.layout()
        old = layout.replaceWidget(self.metadata_edit, new_edit)
        old.widget().deleteLater()
        self.metadata_edit = new_edit

        if hasattr(item, 'name'):
            self.metadata_edit.setTitle(item.name)
