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

from PyQt5 import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets


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


class AnnexedKeyItem(QtGui.QStandardItem):
    def __init__(self, key_obj):
        super().__init__()
        self._obj = key_obj

        self.setText(self.key)

        font = QtGui.QFontDatabase.FixedFont
        font = QtGui.QFontDatabase().systemFont(font)
        self.setFont(font)

        icon = QtWidgets.QFileIconProvider.File
        icon = QtWidgets.QFileIconProvider().icon(icon)
        self.setIcon(icon)

        self.setSelectable(True)
        self.setEditable(False)
        self.setEnabled(True)

    @property
    def metadata(self):
        return self._obj.metadata

    @property
    def key(self):
        return self._obj.key

    def type(self):
        return QtGui.QStandardItem.UserType + 1

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args=self._obj.key,
        )


class AnnexedFieldItem(QtGui.QStandardItem):
    def __init__(self, key_item, field):
        super().__init__()
        self._item = key_item
        self._field = field

        self.setSelectable(True)
        self.setEditable(True)
        self.setEnabled(True)

    @property
    def metadata(self):
        return self._item.metadata.get(self._field, set())

    @metadata.setter
    def metadata(self, value):
        self._item.metadata[self._field] = value
        self.emitDataChanged()

    def type(self):
        return QtGui.QStandardItem.UserType + 2

    def data(self, role=Qt.Qt.DisplayRole):
        if role == Qt.Qt.DisplayRole:
            data = self.metadata

            if len(data) == 0:
                return None
            if len(data) == 1:
                return data.pop()
            else:
                return "<{n} values>".format(n=len(data))

        elif role == Qt.Qt.EditRole:
            data = self.metadata
            if data:
                return str(data)

        elif role == Qt.Qt.ToolTipRole:
            data = self.metadata
            if data:
                return str(data)

        else:
            return super().data(role=role)

    def setData(self, value, role=Qt.Qt.EditRole):
        if role == Qt.Qt.DisplayRole:
            return False

        elif role == Qt.Qt.EditRole:
            try:
                self.metadata = parse_as_set(value)
            except:
                return

        else:
            super().setData(value, role=role)

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args={
                'item': self._item,
                'field': self._field,
            }
        )


class AnnexedKeyMetadataModel(QtGui.QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setRepo(self, repo):
        self.beginResetModel()

        self.repo = repo
        self.fields = ['Git-Annex Key']
        self.key_items = {}
        self._pending = iter(self.repo.annex.values())
        self.clear()

        self.endResetModel()

        QtCore.QMetaObject.invokeMethod(
            self, '_populate',
            Qt.Qt.QueuedConnection,
        )

    @QtCore.pyqtSlot()
    def _populate(self):
        try:
            endtime = time.monotonic() + 0.1
            while time.monotonic() < endtime:
                obj = next(self._pending)
                self.insert_key(obj)

        except StopIteration:
            pass

        else:
            QtCore.QMetaObject.invokeMethod(
                self, '_populate',
                Qt.Qt.QueuedConnection,
            )

    def insert_key(self, key_obj):
        key_item = AnnexedKeyItem(key_obj)
        field_items = (
            AnnexedFieldItem(key_obj, field)
            for field in self.fields[1:]
        )
        self.appendRow([key_item, *field_items])
        self.key_items[key_item.key] = key_item

        new_fields = set(key_item.metadata) - set(self.fields)
        for field in new_fields:
            QtCore.QMetaObject.invokeMethod(
                self, 'insert_field',
                Qt.Qt.QueuedConnection,
                QtCore.Q_ARG(str, field)
            )

    @QtCore.pyqtSlot(str)
    def insert_field(self, field):
        if field in self.fields:
            return
        col = bisect.bisect(self.fields, field, lo=1)
        items = [
            AnnexedFieldItem(self.item(row, 0), field)
            for row in range(self.rowCount())
        ]
        self.insertColumn(col, items)
        self.fields.insert(col, field)
        self.setHorizontalHeaderLabels(self.fields)

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args=self.repo,
        )
