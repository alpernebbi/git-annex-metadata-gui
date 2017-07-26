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


def parse_as_set(x):
    if x == '{}':
        return set()

    try:
        xs = ast.literal_eval(x)
        assert isinstance(xs, set)
        return xs

    except Exception as err:
        fmt = "Can't interpret '{}' as a set."
        msg = fmt.format(x)
        raise ValueError(msg) from err


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
        if not self._index_in_table(index):
            return None

        row, col = index.row(), index.column()

        if role == Qt.Qt.DisplayRole:
            data = self._get_field(row, col)

            if not data:
                return None

            if isinstance(data, str):
                return data

            elif isinstance(data, set):
                if len(data) > 1:
                    return "<{n} values>".format(n=len(data))
                else:
                    return data.pop()

        elif role == Qt.Qt.EditRole:
            data = self._get_field(row, col)

            if not data:
                return None
            else:
                return str(data)

    def headerData(self, section, orientation, role=Qt.Qt.DisplayRole):
        if orientation == Qt.Qt.Horizontal:
            if not 0 <= section < len(self.fields):
                return None

            if section == 0:
                field = 'Git-Annex Key'
            else:
                field = self.fields[section]

            if role == Qt.Qt.DisplayRole:
                return field

        elif orientation == Qt.Qt.Vertical:
            if role == Qt.Qt.DisplayRole:
                return section + 1

    def setData(self, index, value, role=Qt.Qt.EditRole):
        if not self._index_in_fields(index):
            return False

        row, col = index.row(), index.column()

        if role == Qt.Qt.EditRole:
            try:
                value = parse_as_set(value)
                self._set_field(row, col, value)
                return True

            except:
                return False

        return False

    def flags(self, index):
        if not self._index_in_table(index):
            return Qt.Qt.NoItemFlags

        row, col = index.row(), index.column()

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

    def _index_in_table(self, index):
        return index.isValid() \
            and 0 <= index.row() < len(self.objects) \
            and 0 <= index.column() < len(self.fields)

    def _index_in_keys(self, index):
        return index.isValid() \
            and 0 <= index.row() < len(self.objects) \
            and index.column() == 0

    def _index_in_fields(self, index):
        return index.isValid() \
            and 0 <= index.row() < len(self.objects) \
            and 0 < index.column() < len(self.fields)

    def _get_field(self, row, col):
        obj = self.objects[row]
        if col == 0:
            return obj.key

        field = self.fields[col]
        return obj.metadata.get(field, set())

    def _set_field(self, row, col, value):
        obj = self.objects[row]
        field = self.fields[col]
        obj.metadata[field] = value

        index = self.index(row, col)
        self.dataChanged.emit(index, index)

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args=self.repo.workdir,
        )
