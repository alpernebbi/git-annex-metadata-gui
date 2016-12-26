# Git-Annex-Metadata-Gui Models
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

import collections.abc
import json
import os
import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtGui import QStandardItem
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import QFileIconProvider

from git_annex_adapter import GitAnnexMetadata
from git_annex_adapter import GitAnnex


class GitAnnexKeysModel(QStandardItemModel):
    def __init__(self, annex):
        super().__init__()
        self.annex = annex
        self.headers = [('key', 'Git-Annex Key')]

        items = (
            self.annex[key].field('key')
            for key in self.annex.keys(absent=True, cached=True)
        )
        self.appendColumn(items)

        fields = sorted(self.annex.fields(cached=True))
        self.new_field(*fields)

    def flags(self, index):
        item = self.itemFromIndex(index)
        if isinstance(item, GitAnnexFieldItem):
            if item.field == 'key':
                return Qt.ItemIsEnabled \
                       | Qt.ItemIsSelectable
            else:
                return Qt.ItemIsEnabled \
                       | Qt.ItemIsSelectable \
                       | Qt.ItemIsEditable
        else:
            return Qt.NoItemFlags

    def new_field(self, *fields):
        self.headers.extend((f, f.title()) for f in fields)
        items = [self.item(r).item for r in range(self.rowCount())]
        for f in fields:
            new_column = [item.field(f) for item in items]
            self.insertColumn(self.columnCount(), new_column)
        self.setHorizontalHeaderLabels(n for (_, n) in self.headers)

    def __repr__(self):
        repr_ = 'GitAnnexKeysModel(annex={!r}, headers={!r})'
        return repr_.format(self.annex, self.headers)


class GitAnnexFilesModel(QStandardItemModel):
    def __init__(self, annex):
        super().__init__()
        self.annex = annex
        self.headers = [('file', 'Filename')]

        dir_items = {'': self.invisibleRootItem()}

        def make_dir_item(dir_):
            if dir_ in dir_items:
                return dir_items[dir_]
            dir_item = GitAnnexDirectoryItem(dir_, field='file')
            dir_items[dir_] = dir_item
            parent = os.path.dirname(dir_)
            parent_item = make_dir_item(parent)
            parent_item.appendRow(dir_item)
            return dir_item

        metadata = self.annex.metadata(cached=True)
        files = {meta['file']: meta['key'] for meta in metadata}
        for dir_ in map(os.path.dirname, files.keys()):
            make_dir_item(dir_)

        for file, key in files.items():
            item = self.annex[file].field('file', copy=True)
            parent = dir_items[os.path.dirname(file)]
            parent.appendRow(item)

        fields = sorted(self.annex.fields(cached=True))
        self.new_field(*fields)

    def flags(self, index):
        item = self.itemFromIndex(index)
        if isinstance(item, GitAnnexDirectoryItem):
            return Qt.ItemIsEnabled
        elif isinstance(item, GitAnnexFieldItem):
            if item.field == 'file':
                return Qt.ItemIsEnabled \
                       | Qt.ItemIsSelectable
            else:
                return Qt.ItemIsEnabled \
                       | Qt.ItemIsSelectable \
                       | Qt.ItemIsEditable
        else:
            return Qt.NoItemFlags

    def new_field(self, *fields):
        self.headers.extend((f, f.title()) for f in fields)
        columns = [self.columnCount() + i for i in range(len(fields))]

        def make_field_item(item, column, field):
            if isinstance(item, GitAnnexFieldItem):
                return item.item.field(field, copy=True)
            elif isinstance(item, GitAnnexDirectoryItem):
                return GitAnnexDirectoryItem(item.path, column, field)

        def make_field_columns(dir_):
            if isinstance(dir_, QStandardItemModel):
                items = [dir_.item(r) for r in range(dir_.rowCount())]
            elif isinstance(dir_, QStandardItem):
                items = [dir_.child(r) for r in range(dir_.rowCount())]
            else:
                raise RuntimeError()

            for item in items:
                if isinstance(item, GitAnnexDirectoryItem):
                    make_field_columns(item)

            for c, f in zip(columns, fields):
                new_column = [make_field_item(i, c, f) for i in items]
                dir_.insertColumn(c, new_column)

        make_field_columns(self)
        self.setHorizontalHeaderLabels(n for (_, n) in self.headers)

    def __repr__(self):
        repr_ = 'GitAnnexFilesModel(annex={!r}, headers={!r})'
        return repr_.format(self.annex, self.headers)


class GitAnnexWrapper(GitAnnex):
    def __init__(self, path):
        super().__init__(path)
        self.key_items = {}

    def __getitem__(self, map_key):
        if map_key in self.files(cached=True):
            key, file = self.lookupkey(map_key), map_key
            return GitAnnexFileMetadata(self[key], file)

        elif self.examinekey(map_key):
            key, file = map_key, None
            if key in self.key_items:
                return self.key_items[key]
            else:
                self.key_items[key] = GitAnnexKeyMetadata(self, key)
                return self.key_items[key]

        else:
            raise KeyError(map_key)

    def __repr__(self):
        repr_ = 'GitAnnexWrapper(path={!r})'
        return repr_.format(self.path)


class GitAnnexKeyMetadata(GitAnnexMetadata):
    def __init__(self, annex, key):
        super().__init__(annex, key)
        self.field_items = {}

    def field(self, field, copy=False):
        if field in self.field_items:
            item = self.field_items[field]
            return item.copy() if copy else item
        else:
            self.field_items[field] = GitAnnexFieldItem(self, field)
            return self.field_items[field]

    def __repr__(self):
        repr_ = 'GitAnnexKeyMetadata(key={!r}, annex={!r})'
        return repr_.format(self.key, self.annex)


class GitAnnexFileMetadata(collections.abc.MutableMapping):
    def __init__(self, key_item, file):
        self._item = key_item
        self.file = file
        self.field_item = None

    def field(self, field, copy=False):
        if field != 'file':
            return self._item.field(field, copy=copy)
        elif self.field_item:
            return self.field_item
        else:
            self.field_item = GitAnnexFieldItem(self, 'file')
            return self.field_item

    def fields(self, **fields):
        return self._item.fields(**fields)

    def locate(self, absolute=False):
        return self._item.locate(absolute=absolute)

    def __getitem__(self, meta_key):
        if meta_key == 'file':
            return [self.file]
        else:
            return self._item.__getitem__(meta_key)

    def __setitem__(self, meta_key, value):
        return self._item.__setitem__(meta_key, value)

    def __delitem__(self, meta_key):
        return self._item.__delitem__(meta_key)

    def __contains__(self, meta_key):
        return self._item.__contains__(meta_key)

    def __iter__(self):
        return self._item.__iter__()

    def __len__(self):
        return self._item.__len__()

    def __repr__(self):
        repr_ = 'GitAnnexFileMetadata(file={!r}, item={!r})'
        return repr_.format(self.file, self._item)


class GitAnnexFieldItem(QStandardItem):
    qt_type = QStandardItem.UserType + 1

    def __init__(self, item, field, master=None):
        super().__init__()
        self.item = item
        self.field = field

        self.master = master
        self.copies = []

    @property
    def value(self):
        return self.item[self.field]

    @value.setter
    def value(self, value):
        try:
            self.item[self.field] = value
        except KeyError as err:
            msg = "{} couldn't be set to {}."
            print(msg.format(self.field, value))
        finally:
            self.emitDataChanged()
            if self.master:
                self.master.copy_changed(self)
            else:
                self.copy_changed(self)
            self.directory_changed()

    def copy(self):
        if self.master:
            return self.master.copy()
        else:
            copy_ = GitAnnexFieldItem(self.item, self.field, self)
            self.copies.append(copy_)
            return copy_

    def copy_changed(self, origin):
        for copy in self.copies:
            if copy != origin:
                copy.emitDataChanged()

    def directory_changed(self):
        dir_name_item = self.parent()
        if not dir_name_item:
            return

        model = self.model()
        dir_name_index = model.indexFromItem(dir_name_item)
        row, col = dir_name_index.row(), self.column()
        dir_field_index = dir_name_index.sibling(row, col)
        dir_field_item = model.itemFromIndex(dir_field_index)
        dir_field_item.emitDataChanged()

    def data(self, role=Qt.DisplayRole, *args, **kwargs):
        if role == Qt.DisplayRole:
            value = self.collapsed_format(self.value)
            if isinstance(value, str) and value.isnumeric():
                value = int(value)
            if self.field == 'file':
                value = os.path.basename(value)
            return value

        elif role == Qt.DecorationRole:
            if self.field == 'file':
                icon_type = QFileIconProvider.File
                return QFileIconProvider().icon(icon_type)

        elif role == Qt.ToolTipRole:
            if len(self.value) > 1:
                return json.dumps(self.value)

        elif role == Qt.EditRole:
            return json.dumps(self.value)

        elif role == Qt.FontRole:
            fontdb = QFontDatabase()
            if self.field == 'key':
                return fontdb.systemFont(QFontDatabase.FixedFont)
            else:
                return fontdb.systemFont(QFontDatabase.GeneralFont)

        elif role == Qt.UserRole:
            return self.value

    def setData(self, value, role=Qt.DisplayRole, *args, **kwargs):
        if self.field in ('key', 'file'):
            pass

        elif role == Qt.EditRole:
            self.value = json.loads(value)

        elif role == Qt.UserRole:
            self.value = value

    def type(self):
        return self.qt_type

    @staticmethod
    def collapsed_format(value):
        if len(value) > 1:
            value = '<{} values>'.format(len(value))
        elif len(value) == 1:
            value = value[0]
        else:
            value = None
        return value

    @staticmethod
    def collapsed_parse(value):
        pattern = '<\d+ values>'
        if isinstance(value, str) and re.fullmatch(pattern, value):
            raise ValueError('Can\'t infer values')
        if not isinstance(value, list):
            value = [value]
        return value

    def __lt__(self, other):
        if isinstance(other, GitAnnexDirectoryItem):
            return False
        else:
            return super().__lt__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __repr__(self):
        return 'GitAnnexFieldItem(item={!r}, field={!r})'.format(
            self.item, self.field)


class GitAnnexDirectoryItem(QStandardItem):
    qt_type = QStandardItem.UserType + 2

    def __init__(self, path, column=0, field='file'):
        super().__init__()
        self.path = path
        self.column = column
        self.field = field

    def data(self, role=Qt.DisplayRole, *args, **kwargs):
        if self.column != 0:
            return self.column_data(role, *args, **kwargs)

        if role == Qt.DisplayRole:
            return os.path.basename(self.path)

        elif role == Qt.DecorationRole:
            icon_type = QFileIconProvider.Folder
            return QFileIconProvider().icon(icon_type)

        elif role == Qt.ToolTipRole:
            if self.path != os.path.basename(self.path):
                return self.path

        elif role == Qt.FontRole:
            fontdb = QFontDatabase()
            return fontdb.systemFont(QFontDatabase.GeneralFont)

    def column_data(self, role=Qt.DisplayRole, *args, **kwargs):
        parent_root = self.parent() or self.model().invisibleRootItem()
        folder_root = parent_root.child(self.row(), 0)
        responses = set(
            folder_root.child(row, self.column)
            .data(role, *args, **kwargs)
            for row in range(folder_root.rowCount())
        )
        if len(responses) == 1:
            return responses.pop()

    def type(self):
        return self.qt_type

    def __lt__(self, other):
        if isinstance(other, GitAnnexFieldItem):
            return False
        else:
            return super().__lt__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __repr__(self):
        return 'GitAnnexDirectoryItem(path={!r}, field={!r})'.format(
            self.path, self.field)
