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

from PyQt5 import Qt
from PyQt5 import QtCore
from PyQt5 import QtWidgets

from auto_size_line_edit import AutoSizeLineEdit
from field_item_edit import FieldItemEdit

class MetadataEdit(QtWidgets.QGroupBox):
    new_field_requested = QtCore.pyqtSignal(str)

    def __init__(self, key_item, parent=None):
        super().__init__(parent)
        self._item = key_item
        self._fields = []

        self.setTitle(key_item.key)

        layout = QtWidgets.QFormLayout(self)
        growth_policy = QtWidgets.QFormLayout.FieldsStayAtSizeHint
        layout.setFieldGrowthPolicy(growth_policy)
        self.setLayout(layout)

        model = self._item.model()
        model.columnsInserted.connect(self.update_fields)
        self.new_field_requested.connect(model.insert_field)

        line_edit = AutoSizeLineEdit()
        line_edit.editingFinished.connect(self._on_editing_finished)
        self.layout().addRow(line_edit, QtWidgets.QWidget())
        self._new_field_edit = line_edit

        self.update_fields()

    def field_count(self):
        return self.layout().rowCount() - 1

    def update_fields(self):
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
                self.field_count(),
                "{}: ".format(field),
                FieldItemEdit(field_item, parent=self),
            )

    def _on_editing_finished(self):
        field = self._new_field_edit.text()
        if field:
            self._new_field_edit.clear()
            self.new_field_requested.emit(field)

