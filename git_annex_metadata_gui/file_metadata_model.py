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

import collections
import logging
import random
import pygit2

from PyQt5 import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

from git_annex_adapter.repo import AnnexedFile
from git_annex_adapter.repo import AnnexedFileTree

from .utils import AutoConsumed
from .utils import DataProxyItem

logger = logging.getLogger(__name__)


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

    @property
    def name(self):
        return self._name

    @property
    def contentlocation(self):
        return self._item.contentlocation

    def type(self):
        return QtGui.QStandardItem.UserType + 4

    def data(self, role=Qt.Qt.DisplayRole):
        if role == Qt.Qt.DisplayRole:
            return self._name
        if role == Qt.Qt.ToolTipRole:
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


class AnnexedFileFieldItem(DataProxyItem):
    def __init__(self, field_item, filename):
        super().__init__(field_item)
        self._name = filename

    @property
    def key(self):
        return self._item.key

    @property
    def name(self):
        return self._name

    @property
    def contentlocation(self):
        return self._item.contentlocation


class AnnexedDirectoryItem(QtGui.QStandardItem):
    def __init__(self, dirname):
        super().__init__()
        self._name = dirname

        self.setText(self._name)
        self.setToolTip(self._name)

        icon = QtWidgets.QFileIconProvider.Folder
        icon = QtWidgets.QFileIconProvider().icon(icon)
        self.setIcon(icon)

        self.setSelectable(True)
        self.setEditable(False)
        self.setEnabled(True)

    def type(self):
        return QtGui.QStandardItem.UserType + 6

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
        return QtGui.QStandardItem.UserType + 7

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
        self._pending_files = collections.defaultdict(list)

    def setSourceModel(self, model):
        self._model = model

        model.columnsInserted.connect(self._on_columns_inserted)
        model.headerDataChanged.connect(self._on_header_data_changed)
        model.modelReset.connect(self.setTreeish)
        model.key_inserted.connect(self._on_key_inserted)

        if self._model.repo:
            self.setTreeish()

    @property
    def fields(self):
        return self._model.fields

    @QtCore.pyqtSlot(str)
    def insert_field(self, field):
        return self._model.insert_field(field)

    @QtCore.pyqtSlot()
    @QtCore.pyqtSlot(str)
    def setTreeish(self, treeish=None):
        if treeish is None:
            treeish = self._treeish

        if treeish is None:
            treeish = 'HEAD'

        if self._build_tree.running():
            msg = "Aborted loading previous tree model."
            logger.info(msg)
            self._build_tree.stop()

        self._treeish = treeish
        self._pending_files = collections.defaultdict(list)
        self.clear()

        headers = ['Filename', *self._model.fields[1:]]
        self.setHorizontalHeaderLabels(headers)

        self._build_tree.start()

    @QtCore.pyqtSlot()
    @AutoConsumed
    def _build_tree(self):
        msg = "Loading tree model..."
        logger.info(msg)

        PendingObject = collections.namedtuple(
            'PendingObject',
            ['object', 'name', 'parent'],
        )

        pending = collections.deque()

        root = self._model.repo.annex.get_file_tree(self._treeish)
        root_item = self.invisibleRootItem()
        for name_, obj_ in root.items():
            p = PendingObject(obj_, name_, root_item)
            pending.append(p)
            yield

        while pending:
            obj, name, parent = pending.pop()

            if isinstance(obj, pygit2.Blob):
                pass

            elif isinstance(obj, AnnexedFileTree):
                item = AnnexedDirectoryItem(name)
                field_items = [
                    AnnexedDirectoryFieldItem(item)
                    for c in range(1, self._model.columnCount())
                ]
                parent.appendRow([item, *field_items])

                for field_item in field_items:
                    p = PendingObject(field_item, name, parent)
                    pending.append(p)

                for name_, obj_ in obj.items():
                    p = PendingObject(obj_, name_, item)
                    pending.append(p)

            elif isinstance(obj, AnnexedFile):
                if obj.key in self._model.key_items:
                    key_item = self._model.key_items[obj.key]
                    self.insert_file(key_item, name, parent)
                else:
                    f = PendingObject(obj, name, parent)
                    self._pending_files[obj.key].append(f)

            elif isinstance(obj, AnnexedDirectoryFieldItem):
                obj._connect()

            yield

        if self._pending_files:
            msg = "Tree model folders loaded, waiting for key model..."
        else:
            msg = "Tree model fully loaded."
        logger.info(msg)

    def insert_file(self, key_item, name, parent=None):
        if parent is None:
            parent = self.invisibleRootItem()

        file_item = AnnexedFileItem(key_item, name)

        def file_field_item(col):
            field_item = self._model.item(key_item.row(), col)
            return AnnexedFileFieldItem(field_item, name)

        file_field_items = (
            file_field_item(c)
            for c in range(1, self._model.columnCount())
        )

        parent.appendRow([file_item, *file_field_items])

    def _on_key_inserted(self, key):
        for (_, name, parent) in self._pending_files[key]:
            key_item = self._model.key_items[key]
            self.insert_file(key_item, name, parent)
        self._pending_files[key].clear()

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
                return AnnexedFileFieldItem(field_item, item.name)

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

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args=self._model,
        )
