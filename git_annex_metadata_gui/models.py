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

import time

from PyQt5 import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui


class AnnexedKeyMetadataModel(QtGui.QStandardItemModel):
    def __init__(self, repo, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.fields = []

        self._keys_to_add = iter(repo.annex)
        QtCore.QMetaObject.invokeMethod(
            self, '_add_next_keys',
            Qt.Qt.QueuedConnection,
            QtCore.Q_ARG(float, 0.1),
        )

    @QtCore.pyqtSlot(float)
    def _add_next_keys(self, interval=0.0):
        try:
            endtime = time.monotonic() + interval
            while interval == 0 or time.monotonic() < endtime:
                key = next(self._keys_to_add)
                self.add_key(key)

        except StopIteration:
            return

        else:
            QtCore.QMetaObject.invokeMethod(
                self, '_add_next_keys',
                Qt.Qt.QueuedConnection,
                QtCore.Q_ARG(float, interval),
            )

    @QtCore.pyqtSlot(str)
    def add_key(self, key):
        key_obj = self.repo.annex[key]
        key_item = AnnexedKeyItem(key_obj)

        new_fields = set(key_obj.metadata) - set(self.fields)
        for field in new_fields:
            self.add_field(field)

        field_items = (
            key_item.field_item(field)
            for field in self.fields
        )

        self.appendRow([key_item, *field_items])

    @QtCore.pyqtSlot(str)
    def add_field(self, field):
        new_items = [
            self.item(i, 0).field_item(field)
            for i in range(self.rowCount())
        ]

        self.fields.append(field),
        self.fields.sort()
        idx = self.fields.index(field) + 1
        self.insertColumn(idx, new_items)

        self.setHorizontalHeaderLabels(
            ['Git-Annex Key', *self.fields],
        )

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args=self.repo,
        )


class AnnexedMetadataFieldItem(QtGui.QStandardItem):
    def __init__(self, key_item, field):
        super().__init__(key_item)
        self._key_item = key_item
        self._field = field

    def data(self, role=Qt.Qt.DisplayRole):
        if role == Qt.Qt.DisplayRole:
            try:
                metadata = self._key_item._key_obj.metadata
                return str(metadata[self._field])
            except KeyError:
                return None

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args={
                'key_item': self._key_item,
                'field': self._field,
            },
        )


class AnnexedKeyItem(QtGui.QStandardItem):
    def __init__(self, key_obj, parent=None):
        super().__init__(parent)
        self._key_obj = key_obj

    def data(self, role=Qt.Qt.DisplayRole):
        if role == Qt.Qt.DisplayRole:
            return self._key_obj.key

    def field_item(self, field):
        return AnnexedMetadataFieldItem(self, field)

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args=self._key_obj.key,
        )

