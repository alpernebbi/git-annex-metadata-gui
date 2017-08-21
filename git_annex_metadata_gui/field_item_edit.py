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

from PyQt5 import Qt
from PyQt5 import QtCore
from PyQt5 import QtWidgets

try:
    from .auto_size_line_edit import AutoSizeLineEdit
except ImportError:
    from auto_size_line_edit import AutoSizeLineEdit

logger = logging.getLogger(__name__)


class FieldItemEdit(QtWidgets.QWidget):
    cleared = QtCore.pyqtSignal()

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self._item = item
        self._values = []

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        model = self._item.model()
        model.dataChanged.connect(self._on_data_changed)

        append_button = QtWidgets.QPushButton()
        append_button.setText('+')
        append_button.setMaximumWidth(32)
        append_button.clicked.connect(self._on_append_button_clicked)
        self.layout().addWidget(append_button)

        self.update_widgets()

    def widget_count(self):
        return self.layout().count() - 1

    def _on_data_changed(self, topLeft, bottomRight, roles):
        rows = range(topLeft.row(), bottomRight.row() + 1)
        columns = range(topLeft.column(), bottomRight.column() + 1)

        if self._item.row() in rows and self._item.column() in columns:
            self.update_widgets()

    def create_widget(self):
        widget = AutoSizeLineEdit()
        widget.editingFinished.connect(self._on_editing_finished)
        widget.setClearButtonEnabled(True)
        widget.setAlignment(Qt.Qt.AlignCenter)
        return widget

    def update_widgets(self):
        values = self._item.data(Qt.Qt.UserRole)

        for v in set(self._values) - values:
            self._values.remove(v)

        new_values = sorted(values - set(self._values))
        self._values.extend(new_values)

        while self.widget_count() > len(self._values):
            child = self.layout().takeAt(self.widget_count() - 1)
            widget = child.widget()
            widget.deleteLater()

            if self.widget_count() == 0:
                self.cleared.emit()

        while self.widget_count() < len(self._values):
            widget = self.create_widget()
            self.layout().insertWidget(self.widget_count(), widget)

        for idx in range(self.widget_count()):
            widget = self.layout().itemAt(idx).widget()
            if idx < len(self._values):
                widget.setText(self._values[idx])
            else:
                widget.setText('')

        for idx in range(1, self.layout().count()):
            left = self.layout().itemAt(idx - 1).widget()
            right = self.layout().itemAt(idx).widget()
            self.setTabOrder(left, right)

    def _on_editing_finished(self):
        values = []
        for idx in range(self.widget_count()):
            value = self.layout().itemAt(idx).widget().text()
            if value:
                values.append(value)
            if idx < len(self._values) and value != self._values[idx]:
                self._values[idx] = value

        self._item.setData(set(values), role=Qt.Qt.UserRole)

    def _on_append_button_clicked(self):
        button_idx = self.widget_count()
        if button_idx == 0:
            create = True
        else:
            widget_idx = button_idx - 1
            last_widget = self.layout().itemAt(widget_idx).widget()
            create = bool(last_widget.text())

        if create:
            widget = self.create_widget()
            self.layout().insertWidget(button_idx, widget)
        else:
            widget = last_widget

        widget.setFocus()

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args=self._item,
        )

