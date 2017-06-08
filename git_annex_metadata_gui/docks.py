# Git-Annex-Metadata-Gui Docks
# Copyright (C) 2016 Alper Nebi Yasak
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

import mimetypes
from functools import partial

from PyQt5.QtCore import QModelIndex
from PyQt5.QtCore import QSize
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDockWidget
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtWidgets import QWidget


class PreviewDock(QDockWidget):
    def __init__(self):
        super().__init__('File Preview')
        self._area = PreviewDock.ScrollArea()
        self._item = None

        self.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
        )
        self.setWidget(self._area)

    def set_item(self, item):
        self._item = item
        preview = self._area.widget()

        if item is None:
            preview.clear()
            return

        path = item.locate(absolute=True)
        filename = item['file'][0]
        try:
            mime = mimetypes.guess_type(path)[0] \
                   or mimetypes.guess_type(filename)[0] \
                   or ''
        except:
            mime = ''

        if mime.startswith('text/'):
            with open(path) as file:
                text = file.read()
            preview.setText(text)
            preview.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        elif mime.startswith('image/'):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                thumb = pixmap.scaled(
                    self._area.width() * 0.95,
                    self._area.height() * 0.95,
                    Qt.KeepAspectRatio,
                )
                preview.setPixmap(thumb)
                preview.setAlignment(Qt.AlignCenter | Qt.AlignHCenter)
            else:
                preview.clear()
                name = item.file or item.key
                self.statusBar().showMessage(
                    'Couldn\'t preview image {}'.format(name)
                )

        else:
            preview.clear()

    class ScrollArea(QScrollArea):
        def __init__(self):
            super().__init__()
            self._label = PreviewDock.Label()
            self.setWidget(self._label)

            self.setWidgetResizable(True)
            self.setSizeAdjustPolicy(QScrollArea.AdjustToContents)
            self.setMinimumWidth(300)

    class Label(QLabel):
        def __init__(self):
            super().__init__()
            self.setTextFormat(Qt.PlainText)
            self.setFont(
                QFontDatabase().systemFont(QFontDatabase.FixedFont)
            )
            self.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding
            )

        def sizeHint(self):
            return QSize(600, 600)


class MetadataEditorDock(QDockWidget):
    def __init__(self, new_field_creator):
        super().__init__('Metadata Editor')
        self._widget = MetadataEditorDock.Widget()
        self._layout = self._widget.layout()
        self.setWidget(self._widget)
        self._item = None
        self._new_field_creator = new_field_creator
        self._sublayouts = {}

        self.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
        )

    def set_item(self, item):
        for layout in self._sublayouts.values():
            MetadataEditorDock.Layout.clear(layout)
        self._sublayouts = {}
        self._layout.clear()
        self._item = item
        if item is None:
            return

        file_name = self.fontMetrics().elidedText(
            item.file or item.key, Qt.ElideRight,
            self._widget.width() * 0.7,
        )
        self._layout.addRow('File:', QLabel(file_name))

        new_button, new_field = self.create_new_field_row()
        self._layout.addRow(new_button, new_field)

        for field in item:
            self.create_new_field(field)

    def field_count(self):
        return self._layout.rowCount() - 1

    def create_new_field_row(self):
        def handler(widget):
            field = widget.text().lower()
            widget.setText('')
            if not field or field in ['file', 'key']:
                return

            if field not in self._sublayouts:
                self.create_new_field(field)
            layout = self._sublayouts[field]
            append = layout.itemAt(layout.count() - 1).widget()
            append.click()

        line_edit = MetadataEditorDock.EditField()
        line_edit.returnPressed.connect(partial(handler, line_edit))

        button = MetadataEditorDock.AppendButton()
        button.clicked.connect(partial(handler, line_edit))
        return button, line_edit

    def create_new_field(self, field):
        if field not in self._item:
            self._new_field_creator(field)

        field_item = self._item.field(field)
        layout = MetadataEditorDock.EditFieldItems(self, field_item)
        field_label = '{}: '.format(field.title())
        self._layout.insertRow(
            self.field_count(), field_label, layout
        )
        self._sublayouts[field] = layout
        return layout

    def remove_field(self, field):
        if field not in self._sublayouts:
            return

        layout = self._sublayouts[field]
        label = self._layout.labelForField(layout)

        label_index = None
        layout_index = None
        for index in range(self._layout.count()):
            item = self._layout.itemAt(index)
            if item.isEmpty():
                continue
            if label == item.widget():
                label_index = index
            if layout == item.layout():
                layout_index = index

        layout_ = self._layout.takeAt(layout_index).layout()
        label = self._layout.takeAt(label_index).widget()
        MetadataEditorDock.Layout.clear(layout_)
        label.deleteLater()
        del self._sublayouts[field]

    class EditFieldItems(QHBoxLayout):
        def __init__(self, parent, field_item):
            super().__init__()
            self._item = field_item
            self._item.model().dataChanged.connect(
                self.data_changed_handler
            )
            self.parent = parent

            append_button = self.create_append_button()
            self.addWidget(append_button)
            self.data_changed_handler()

        def create_append_button(self):
            button = MetadataEditorDock.AppendButton()
            button.clicked.connect(
                partial(self.clicked_handler, button)
            )
            return button

        def create_widget(self):
            widget = MetadataEditorDock.EditField()
            widget.editingFinished.connect(
                partial(self.editing_finished_handler, widget)
            )
            return widget

        def widget_count(self):
            return self.count() - 1

        def make_widgets(self, length):
            while self.widget_count() > length:
                child = self.takeAt(0)
                widget = child.widget()
                widget.deleteLater()

            while self.widget_count() < length:
                widget = self.create_widget()
                self.insertWidget(self.widget_count(), widget)

        def data_changed_handler(self, model_index=QModelIndex()):
            values = self._item.data(Qt.UserRole)
            self.make_widgets(len(values))
            if not values:
                self.parent.remove_field(self._item.field)

            for index in range(self.widget_count()):
                widget = self.itemAt(index).widget()
                widget.setText(
                    values[index] if len(values) > index else ''
                )

        def editing_finished_handler(self, widget):
            values = self._item.data(Qt.UserRole)
            index = self.indexOf(widget)
            value = widget.text()
            if value:
                if index == len(values):
                    values.append(value)
                elif index < len(values):
                    values[index] = value
            else:
                if len(values) > index >= 0:
                    del values[index]
                if self.widget_count() == 1:
                    self.parent.remove_field(self._item.field)
            widget.clearFocus()
            self._item.setData(values, Qt.UserRole)

        def clicked_handler(self, button):
            widget_count = self.widget_count()
            if widget_count == 0:
                self.make_widgets(1)
                widget_count = 1

            last_widget = self.itemAt(widget_count - 1).widget()
            if last_widget.text():
                self.make_widgets(widget_count + 1)
                new_widget = self.itemAt(widget_count).widget()
                new_widget.setFocus()
            else:
                last_widget.setFocus()

    class EditField(QLineEdit):
        def __init__(self):
            super().__init__()
            self.setAlignment(Qt.AlignCenter)
            self.setClearButtonEnabled(True)

            self.textChanged.connect(self.updateGeometry)

        def sizeHint(self):
            height = super().sizeHint().height()
            min_width = self.minimumSizeHint().width()
            text_width = self.fontMetrics().size(
                Qt.TextSingleLine, self.text()
            ).width()
            if not self.isVisible():
                min_width += 26
            return QSize(text_width + min_width, height)

    class AppendButton(QPushButton):
        def __init__(self):
            super().__init__()
            self.setText('+')
            self.setMaximumWidth(32)

    class Layout(QFormLayout):
        def __init__(self):
            super().__init__()
            self.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)

        def clear(self, sublayout=None):
            if sublayout:
                MetadataEditorDock.Layout.clear(sublayout)
            while self.count():
                child = self.takeAt(0)
                widget = child.widget()
                if widget:
                    widget.deleteLater()
                else:
                    self.clear(child.layout())

    class Widget(QWidget):
        def __init__(self):
            super().__init__()
            self._layout = MetadataEditorDock.Layout()
            self.setLayout(self._layout)
