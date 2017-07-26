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

import ast
import bisect
import time
import types

from git_annex_adapter.repo import GitAnnexRepo

from PyQt5 import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui


class AnnexedKeyMetadataTable(QtCore.QAbstractTableModel):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.repo = GitAnnexRepo(path)

        self.objects = []
        self.fields = [None]
        self._pending = iter(self.repo.annex.values())

        QtCore.QMetaObject.invokeMethod(
            self, '_lazy_init',
            Qt.Qt.QueuedConnection,
        )

    @QtCore.pyqtSlot()
    def _lazy_init(self):
        try:
            endtime = time.monotonic() + 0.1
            while time.monotonic() < endtime:
                obj = next(self._pending)

                self.insert_key(obj)
                for field in obj.metadata:
                    self.insert_field(field)

        except StopIteration:
            return

        else:
            QtCore.QMetaObject.invokeMethod(
                self, '_lazy_init',
                Qt.Qt.QueuedConnection,
            )

    @QtCore.pyqtSlot(str)
    def insert_field(self, field):
        if field not in self.fields:
            col = bisect.bisect(self.fields, field, lo=1)
            self.beginInsertColumns(QtCore.QModelIndex(), col, col)
            self.fields.insert(col, field)
            self.endInsertColumns()

    def insert_key(self, obj):
        row = len(self.objects)
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self.objects.append(obj)
        self.endInsertRows()

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent == QtCore.QModelIndex():
            return len(self.objects)
        else:
            return 0

    def columnCount(self, parent=QtCore.QModelIndex()):
        if parent == QtCore.QModelIndex():
            return len(self.fields)
        else:
            return 0

    def data(self, index, role=Qt.Qt.DisplayRole):
        if not index.isValid():
            return None

        row, col = index.row(), index.column()
        if not 0 <= row < len(self.objects):
            return None
        if not 0 <= col < len(self.fields):
            return None

        if role == Qt.Qt.DisplayRole:
            obj = self.objects[row]
            if col == 0:
                return obj.key

            field_name = self.fields[col]
            try:
                field = obj.metadata[field_name]
                field_str = str(field)
            except KeyError:
                field_str = ''

            return field_str

    def headerData(self, section, orientation, role=Qt.Qt.DisplayRole):
        if orientation == Qt.Qt.Horizontal:
            if section == 0:
                field_name = "Git-Annex Key"
            elif 0 < section < len(self.fields):
                field_name = self.fields[section]
            else:
                return None

            if role == Qt.Qt.DisplayRole:
                return field_name

        elif orientation == Qt.Qt.Vertical:
            if role == Qt.Qt.DisplayRole:
                return section + 1

    def setData(self, index, value, role=Qt.Qt.EditRole):
        if not index.isValid():
            return False

        row, col = index.row(), index.column()
        if not 0 <= row < len(self.objects):
            return False
        if not 1 <= col < len(self.fields):
            return False

        if role == Qt.Qt.EditRole:
            try:
                obj = self.objects[row]
                field_name = self.fields[col]

                field_value = ast.literal_eval(value)
                if field_value == {}:
                    field_value = set()

                obj.metadata[field_name] = field_value
                self.dataChanged.emit(index, index)
                return True

            except:
                return False

        else:
            return False

    def flags(self, index):
        if not index.isValid():
            return Qt.Qt.NoItemFlags

        row, col = index.row(), index.column()
        if not 0 <= row < len(self.objects):
            return Qt.Qt.NoItemFlags
        if not 0 <= col < len(self.fields):
            return Qt.Qt.NoItemFlags

        if col == 0:
            return (
                Qt.Qt.ItemIsSelectable
                | Qt.Qt.ItemIsEnabled
                | Qt.Qt.ItemNeverHasChildren
            )

        else:
            return (
                Qt.Qt.ItemIsSelectable
                | Qt.Qt.ItemIsEditable
                | Qt.Qt.ItemIsEnabled
                | Qt.Qt.ItemNeverHasChildren
            )

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args=self.repo.workdir,
        )
