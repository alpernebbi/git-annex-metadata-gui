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
from git_annex_adapter import GitRepo


class GitAnnexKeysModel(QStandardItemModel):
    def __init__(self, annex):
        super().__init__()
        self.annex = annex
        self.headers = [('key', 'Git-Annex Key')]

        items = (
            self.annex.item(key=key).field('key')
            for key in self.annex.keys(absent=True, cached=True)
        )
        self.appendColumn(items)

        fields = sorted(self.annex.fields(cached=True))
        self.new_field(*fields)

    def flags(self, index):
        item = self.itemFromIndex(index)
        if isinstance(item, GitAnnexField):
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


class GitAnnexFilesModel(QStandardItemModel):
    def __init__(self, annex):
        super().__init__()
        self.annex = annex
        self.headers = [('file', 'Filename')]

        dir_items = {'': self.invisibleRootItem()}

        def make_dir_item(dir_):
            if dir_ in dir_items:
                return dir_items[dir_]
            dir_item = GitAnnexDirectory(dir_, field='file')
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
            item = self.annex.item(key=key, path=file).field('file')
            parent = dir_items[os.path.dirname(file)]
            parent.appendRow(item)

        fields = sorted(self.annex.fields(cached=True))
        self.new_field(*fields)

    def flags(self, index):
        item = self.itemFromIndex(index)
        if isinstance(item, GitAnnexDirectory):
            return Qt.ItemIsEnabled
        elif isinstance(item, GitAnnexField):
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
            if isinstance(item, GitAnnexField):
                return item.item.field(field)
            elif isinstance(item, GitAnnexDirectory):
                return GitAnnexDirectory(item.path, column, field)

        def make_field_columns(dir_):
            if isinstance(dir_, QStandardItemModel):
                items = [dir_.item(r) for r in range(dir_.rowCount())]
            elif isinstance(dir_, QStandardItem):
                items = [dir_.child(r) for r in range(dir_.rowCount())]
            else:
                raise RuntimeError()

            for item in items:
                if isinstance(item, GitAnnexDirectory):
                    make_field_columns(item)

            for c, f in zip(columns, fields):
                new_column = [make_field_item(i, c, f) for i in items]
                dir_.insertColumn(c, new_column)

        make_field_columns(self)
        self.setHorizontalHeaderLabels(n for (_, n) in self.headers)


class GitAnnexWrapper(GitAnnex):
    def __init__(self, path):
        repo = GitRepo(path)
        super().__init__(repo)

    def item(self, key=None, path=None):
        if key:
            return GitAnnexFile(self, key, file=path)
        elif path:
            key = self.lookupkey(path)
            return GitAnnexFile(self, key, file=path)
        else:
            raise ValueError('Requires path or key')


class GitAnnexFile(GitAnnexMetadata):
    def __init__(self, annex, key, file=None):
        super().__init__(annex, key, file=file)
        self.field_items = {}

    def field(self, field):
        if field not in self.field_items:
            self.field_items[field] = GitAnnexField(self, field)
        return self.field_items[field]


class GitAnnexField(QStandardItem):
    qt_type = QStandardItem.UserType + 1

    def __init__(self, item, field):
        super().__init__()
        self.item = item
        self.field = field

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
        if isinstance(other, GitAnnexDirectory):
            return False
        else:
            return super().__lt__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __repr__(self):
        return 'GitAnnexField(item={!r}, field={!r})'.format(
            self.item, self.field)


class GitAnnexDirectory(QStandardItem):
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
        if isinstance(other, GitAnnexField):
            return False
        else:
            return super().__lt__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __repr__(self):
        return 'GitAnnexDirectory(path={!r}, field={!r})'.format(
            self.path, self.field)
