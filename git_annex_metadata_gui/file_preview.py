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

import logging
import mimetypes

from PyQt5 import Qt
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets

logger = logging.getLogger(__name__)


class FilePreview(QtWidgets.QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # These are set by Qt Designer
        self.text_preview = None
        self.graphics_preview = None

    def addWidget(self, widget):
        super().addWidget(widget)
        if isinstance(widget, QtWidgets.QPlainTextEdit):
            self.text_preview = widget
        if isinstance(widget, QtWidgets.QGraphicsView):
            self.graphics_preview = widget

    @QtCore.pyqtSlot()
    def clear(self):
        if self.text_preview is not None:
            self.text_preview.clear()

        if self.graphics_preview is not None:
            old_scene = self.graphics_preview.scene()
            if old_scene:
                old_scene.clear()
                old_scene.deleteLater()

    @QtCore.pyqtSlot(str)
    def preview_text_file(self, path):
        filename = path.split('/')[-1]

        if self.text_preview is None:
            msg = "Text preview widget not created yet."
            logger.critical(msg)
            return

        if not self.isVisible():
            msg = "Preview widget invisible, not previewing text."
            logger.info(msg)
            return

        self.setCurrentWidget(self.text_preview)

        try:
            with open(path, 'r') as file:
                text = file.read()
        except UnicodeDecodeError:
            fmt = "File '{}' should be a UTF-8 text file, but isn't."
            msg = fmt.format(filename)
            logger.error(msg)
            return

        self.text_preview.setPlainText(text)

        fmt = "Previewed file '{}' as plain text."
        msg = fmt.format(filename)
        logger.info(msg)

    @QtCore.pyqtSlot(str)
    def preview_image_file(self, path):
        filename = path.split('/')[-1]

        if self.graphics_preview is None:
            msg = "Graphics preview widget not created yet."
            logger.critical(msg)
            return

        if not self.isVisible():
            msg = "Preview widget invisible, not previewing image."
            logger.info(msg)
            return

        self.setCurrentWidget(self.graphics_preview)

        scene = QtWidgets.QGraphicsScene(self)
        self.graphics_preview.setScene(scene)

        # Using QImage instead of directly creating the QPixmap
        # prevents a segmentation fault in my container setup
        image = QtGui.QImage(path)
        if image.isNull():
            fmt = "File '{}' should be an image, but isn't."
            msg = fmt.format(filename)
            logger.error(msg)
            return

        pixmap = QtGui.QPixmap.fromImage(image)
        if pixmap.isNull():
            fmt = "Failed to generate pixmap from image '{}'."
            msg = fmt.format(filename)
            logger.critical(msg)
            return

        pixmap_item = QtWidgets.QGraphicsPixmapItem(pixmap)
        scene.addItem(pixmap_item)
        self.graphics_preview.fitInView(
            pixmap_item,
            Qt.Qt.KeepAspectRatio,
        )

        fmt = "Previewed file '{}' as an image."
        msg = fmt.format(filename)
        logger.info(msg)

    @QtCore.pyqtSlot(QtGui.QStandardItem)
    def preview_item(self, item):
        self.clear()

        if not hasattr(item, 'key'):
            return

        try:
            name = item.name
        except AttributeError:
            name = None

        try:
            path = item.contentlocation
        except AttributeError:
            fmt = "Item '{}' doesn't have a contentlocation property."
            msg = fmt.format(repr(item))
            logger.critical(msg)
            return

        if not path:
            fmt = "Content for key '{}' is not available."
            msg = fmt.format(item.key)
            logger.error(msg)
            return

        mime, encoding = None, None
        if name:
            mime, encoding = mimetypes.guess_type(name)
        if not mime:
            mime, encoding = mimetypes.guess_type(path)

        if encoding:
            fmt = "Can't decode encoding '{}'."
            msg = fmt.format(encoding)
            logger.error(msg)
            return

        if not mime:
            if hasattr(item, 'name'):
                fmt = "Couldn't recognize mimetype for file '{}' ({})."
                msg = fmt.format(item.name, item.key)
            else:
                fmt = "Couldn't recognize mimetype for key '{}'."
                msg = fmt.format(item.key)
            logger.error(msg)
            return

        if mime.startswith('text/'):
            self.preview_text_file(path)

        elif mime.startswith('image/'):
            self.preview_image_file(path)

        else:
            fmt = "Can't preview mimetype '{}'."
            msg = fmt.format(mime)
            logger.error(msg)
            return

