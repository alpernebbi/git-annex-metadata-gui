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
import collections
import time
import types
import pygit2

from PyQt5 import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from git_annex_adapter.repo import AnnexedFile
from git_annex_adapter.repo import AnnexedFileTree


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
        self.repo = None

    def setRepo(self, repo):
        self.beginResetModel()

        self.repo = repo
        self.fields = ['Git-Annex Key']
        self.key_items = {}
        self._pending = iter(self.repo.annex.values())
        self.clear()
        self.setHorizontalHeaderLabels(self.fields)

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


class DataProxyItem(QtGui.QStandardItem):
    def __init__(self, item):
        super().__init__()
        self._item = item

        model = self._item.model()
        model.dataChanged.connect(self._propagate_changes)

    def type(self):
        return QtGui.QStandardItem.UserType + 3

    def data(self, role=Qt.Qt.DisplayRole):
        return self._item.data(role=role)

    def setData(self, value, role=Qt.Qt.EditRole):
        return self._item.setData(value, role=role)

    def flags(self):
        return self._item.flags()

    def _propagate_changes(self, topLeft, bottomRight, roles):
        rows = range(topLeft.row(), bottomRight.row() + 1)
        columns = range(topLeft.column(), bottomRight.column() + 1)

        if self._item.row() in rows and self._item.column() in columns:
            self.emitDataChanged()

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args=self._item,
        )


class AnnexedFileItem(DataProxyItem):
    def __init__(self, key_item, filename):
        super().__init__(key_item)
        self._name = filename

        self.setSelectable(True)
        self.setEditable(False)
        self.setEnabled(True)

    @property
    def key(self):
        return self._item.key

    def type(self):
        return QtGui.QStandardItem.UserType + 4

    def data(self, role=Qt.Qt.DisplayRole):
        if role == Qt.Qt.DisplayRole:
            return self._name
        if role == Qt.Qt.FontRole:
            return QtGui.QStandardItem.data(self, role=role)
        else:
            return super().data(role=role)

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args={
                'item': self._item,
                'name': self._name,
            },
        )


class AnnexedDirectoryItem(QtGui.QStandardItem):
    def __init__(self, dirname):
        super().__init__()
        self._name = dirname

        self.setText(self._name)

        icon = QtWidgets.QFileIconProvider.Folder
        icon = QtWidgets.QFileIconProvider().icon(icon)
        self.setIcon(icon)

        self.setSelectable(True)
        self.setEditable(False)
        self.setEnabled(True)

    def type(self):
        return QtGui.QStandardItem.UserType + 5

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args=self._name,
        )


class AnnexedDirectoryFieldItem(QtGui.QStandardItem):
    def __init__(self, dir_item):
        super().__init__()
        self._item = dir_item
        self._connected = False
        self._column_data_cache = {}

        self.setSelectable(True)
        self.setEditable(False)
        self.setEnabled(True)

        if self._item.model():
            self._connect()

    def _connect(self):
        if self._connected:
            return

        model = self._item.model()
        model.dataChanged.connect(self._propagate_changes)
        model.layoutChanged.connect(self._emit_data_changed)
        model.modelReset.connect(self._emit_data_changed)
        model.rowsInserted.connect(self._on_rows_inserted)
        model.rowsMoved.connect(self._on_rows_moved)
        model.rowsRemoved.connect(self._on_rows_removed)

        self._connected = True

    def type(self):
        return QtGui.QStandardItem.UserType + 6

    def data(self, role=Qt.Qt.DisplayRole):
        if role == Qt.Qt.DisplayRole:
            return self._column_data(role=role)

        elif role == Qt.Qt.ToolTipRole:
            return self._column_data(role=role)

        else:
            return super().data(role=role)

    def _column_data(self, role=Qt.Qt.DisplayRole):
        if role in self._column_data_cache:
            return self._column_data_cache[role]

        children = (
            self._item.child(row, self.column())
            for row in range(self._item.rowCount())
        )

        responses = set()
        for child in children:
            if child:
                responses.add(child.data(role=role))
            if len(responses) > 1:
                responses.clear()
                break

        if responses:
            data = responses.pop()
        else:
            data = None

        self._column_data_cache[role] = data
        return data

    def _propagate_changes(self, topLeft, bottomRight, roles):
        rows = range(topLeft.row(), bottomRight.row() + 1)
        columns = range(topLeft.column(), bottomRight.column() + 1)

        parent = topLeft.parent()
        if parent != bottomRight.parent():
            self._emit_data_changed()
            return

        if parent != self._item.index():
            return

        if self.column() in columns:
            self._emit_data_changed()

    def _emit_data_changed(self):
        self._column_data_cache.clear()
        self.emitDataChanged()

    def _on_rows_inserted(self, parent, first, last):
        if parent == self._item.index():
            self._emit_data_changed()

    def _on_rows_moved(self, parent, start, end, destination, row):
        if parent == self._item.index():
            self._emit_data_changed()
        if destination == self._item.index():
            self._emit_data_changed()

    def _on_rows_removed(self, parent, first, last):
        if parent == self._item.index():
            self._emit_data_changed()

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args={
                'item': self._item,
                'column': self.column(),
            }
        )


class AnnexedFileMetadataModel(QtGui.QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._treeish = None

    def setSourceModel(self, model):
        self.beginResetModel()
        self._model = model
        self.endResetModel()

        model.columnsInserted.connect(self._on_columns_inserted)
        model.headerDataChanged.connect(self._on_header_data_changed)
        model.modelReset.connect(self.setTreeish)

        if self._model.repo:
            self.setTreeish()

    @QtCore.pyqtSlot()
    @QtCore.pyqtSlot(str)
    def setTreeish(self, treeish=None):
        if treeish is None:
            treeish = self._treeish

        if treeish is None:
            treeish = 'HEAD'

        self.beginResetModel()

        self._treeish = treeish
        self._pending = []
        tree = self._model.repo.annex.get_file_tree(self._treeish)
        self._pending_trees = [(tree, '', None)]
        self.clear()
        self.setHorizontalHeaderLabels(['Filename'])

        self.endResetModel()

        QtCore.QMetaObject.invokeMethod(
            self, '_build_tree',
            Qt.Qt.QueuedConnection,
        )

    @QtCore.pyqtSlot()
    def _build_tree(self):
        PendingFile = collections.namedtuple(
            'PendingFile',
            ['key', 'name', 'parent'],
        )

        PendingTree = collections.namedtuple(
            'PendingTree',
            ['tree', 'name', 'parent'],
        )

        endtime = time.monotonic() + 0.1
        while time.monotonic() < endtime:
            if not self._pending_trees:
                break

            tree, name, parent = self._pending_trees.pop()

            if parent:
                item = AnnexedDirectoryItem(name)
                field_items = [
                    AnnexedDirectoryFieldItem(item)
                    for c in range(1, self._model.columnCount())
                ]
                parent.appendRow([item, *field_items])

                for field_item in field_items:
                    field_item._connect()

            else:
                item = self.invisibleRootItem()

            for name_, obj in tree.items():
                if isinstance(obj, pygit2.Blob):
                    pass

                elif isinstance(obj, AnnexedFile):
                    f = PendingFile(obj.key, name_, item)
                    self._pending.append(f)

                elif isinstance(obj, AnnexedFileTree):
                    t = PendingTree(obj, name_, item)
                    self._pending_trees.append(t)

        else:
            QtCore.QMetaObject.invokeMethod(
                self, '_build_tree',
                Qt.Qt.QueuedConnection,
            )
            return

        if self._pending:
            QtCore.QMetaObject.invokeMethod(
                self, '_populate',
                Qt.Qt.QueuedConnection,
            )

    @QtCore.pyqtSlot()
    def _populate(self):
        try:
            items = iter(self._pending)
            endtime = time.monotonic() + 0.1
            while time.monotonic() < endtime:
                file = next(items)
                obj = self._model.key_items.get(file.key)

                if obj:
                    self.insert_file(obj, file.name, file.parent)
                    self._pending.remove(file)

        except StopIteration:
            pass

        if self._pending:
            QtCore.QMetaObject.invokeMethod(
                self, '_populate',
                Qt.Qt.QueuedConnection,
            )

    def insert_file(self, obj, name, parent=None):
        if parent is None:
            parent = self.invisibleRootItem()

        file_item = AnnexedFileItem(obj, name)
        field_items = (
            DataProxyItem(self._model.item(obj.row(), c))
            for c in range(1, self._model.columnCount())
        )
        parent.appendRow([file_item, *field_items])

    def _on_columns_inserted(self, parent, first, last):
        columns = range(first, last + 1)

        if first == 0:
            return

        for col in columns:
            self._create_column(col)

    def _create_column(self, col, parent=None):
        if parent is None:
            parent = self.invisibleRootItem()

        def _create_field(item):
            if isinstance(item, AnnexedFileItem):
                obj = self._model.key_items.get(item.key)
                field_item = self._model.item(obj.row(), col)
                return DataProxyItem(field_item)

            elif isinstance(item, AnnexedDirectoryItem):
                return AnnexedDirectoryFieldItem(item)

        field_items = [
            _create_field(parent.child(i))
            for i in range(parent.rowCount())
        ]
        parent.insertColumn(col, field_items)

        for i in range(parent.rowCount()):
            child = parent.child(i)
            if isinstance(child, AnnexedDirectoryItem):
                self._create_column(col, parent=child)

    def _on_header_data_changed(self, orientation, first, last):
        if orientation == Qt.Qt.Horizontal:
            labels = ['Filename', *self._model.fields[1:]]
            self.setHorizontalHeaderLabels(labels)
