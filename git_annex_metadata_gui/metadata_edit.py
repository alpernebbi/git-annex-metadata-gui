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

import sip

from PyQt5 import Qt
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets

try:
    from .auto_size_line_edit import AutoSizeLineEdit
    from .field_item_edit import FieldItemEdit
except ImportError:
    from auto_size_line_edit import AutoSizeLineEdit
    from field_item_edit import FieldItemEdit

class MetadataEdit(QtWidgets.QGroupBox):
    new_field_requested = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item = None
        self._fields = []
        self._new_field_edit = None
        self.clear()

    @QtCore.pyqtSlot(QtGui.QStandardItem)
    def set_item(self, item):
        self.clear()

        if not self.isVisible():
            return

        if not hasattr(item, 'key'):
            return
        self._item = item

        if hasattr(item, 'name'):
            self.setTitle(item.name)
        else:
            self.setTitle(item.key)

        model = self._item.model()
        model.columnsInserted.connect(self._on_columns_inserted)
        model.modelReset.connect(self.clear)
        self.new_field_requested.connect(model.insert_field)

        if self._new_field_edit is None:
            line_edit = AutoSizeLineEdit()
            line_edit.editingFinished.connect(self._request_new_field)
            self.layout().addRow(line_edit, QtWidgets.QWidget())
            self._new_field_edit = line_edit

        self.update_fields()

    @QtCore.pyqtSlot()
    def clear(self):
        try:
            model = self._item.model()
        except (AttributeError, RuntimeError):
            pass
        else:
            model.columnsInserted.disconnect(self._on_columns_inserted)
            self.new_field_requested.disconnect(model.insert_field)

        self._item = None
        self._fields = []
        self._new_field_edit = None
        self.setTitle('')

        if self.layout() is not None:
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item:
                    item.widget().deleteLater()
            sip.delete(self.layout())

        layout = QtWidgets.QFormLayout()
        layout.setFieldGrowthPolicy(layout.FieldsStayAtSizeHint)
        self.setLayout(layout)

    def update_fields(self):
        if self._item is None:
            return

        model = self._item.model()
        parent = self._item.parent()
        if not parent:
            parent = model.invisibleRootItem()
        row = self._item.row()

        for col, field in enumerate(model.fields[1:], 1):
            if field in self._fields:
                continue
            self._fields.append(field)
            field_item = parent.child(row, col)
            self.layout().insertRow(
                self.layout().rowCount() - 1,
                "{}: ".format(field),
                FieldItemEdit(field_item, parent=self),
            )

    def setTitle(self, title):
        if len(title) > 48:
            title = "{:.45}...".format(title)
        super().setTitle(title)

    def _request_new_field(self):
        field = self._new_field_edit.text()
        if field:
            self._new_field_edit.clear()
            self.new_field_requested.emit(field)

    def _on_columns_inserted(self, parent, first, last):
        if self._item is None:
            return

        parent_ = self._item.parent()
        if not parent_:
            parent_ = self._item.model().invisibleRootItem()
        parent_ = parent_.index()

        if parent == parent_:
            self.update_fields()

