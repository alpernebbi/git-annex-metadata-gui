#!/usr/bin/env python3

import sys
import subprocess
import json
import re
import os
import collections.abc
from functools import partial
from collections import defaultdict

from PyQt5.QtCore import Qt
from PyQt5.QtCore import QAbstractItemModel
from PyQt5.QtCore import QAbstractTableModel
from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QTreeView
from PyQt5.QtWidgets import QTableView
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtWidgets import QFileIconProvider


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    if sys.argv and len(sys.argv) > 1:
        window.load_repository(sys.argv[1])
    window.show()
    sys.exit(app.exec_())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(800, 600)
        self.setWindowTitle('Git Annex Metadata Editor')

        self.create_actions()
        self.create_menus()
        self.create_center_widget()
        self.create_statusbar()

    def create_actions(self):
        self.open_action = QAction(
            "Open...", self,
            shortcut="Ctrl+O",
            statusTip="Open an existing directory",
            triggered=self.open_directory
        )

        self.exit_action = QAction(
            "Exit", self,
            shortcut="Ctrl+Q",
            statusTip="Exit the application",
            triggered=self.close,
        )

    def create_menus(self):
        self.file_menu = self.menuBar().addMenu('&File')
        self.file_menu.addAction(self.open_action)
        self.file_menu.addAction(self.exit_action)

        self.header_menu = self.menuBar().addMenu('&Header')
        self.header_menu.setDisabled(True)

    def create_center_widget(self):
        self.view_tabs = QTabWidget()

        self.files_view = QTreeView()
        self.files_view.setSortingEnabled(True)
        self.view_tabs.addTab(self.files_view, 'Files')

        self.keys_view = QTableView()
        self.keys_view .setSortingEnabled(True)
        self.view_tabs.addTab(self.keys_view, 'Keys')

        self.setCentralWidget(self.view_tabs)

    def create_statusbar(self):
        self.statusBar().showMessage('Ready')

    def load_repository(self, dir_name):
        try:
            self.keys_model = GitAnnexKeysModel(dir_name)
            self.files_model = GitAnnexFilesModel(dir_name)
            self.refresh_views()
            self.populate_header_menu()
        except subprocess.CalledProcessError as err:
            msg = 'Couldn\'t load "{}" as a git-annex repo'
            self.statusBar().showMessage(msg.format(dir_name))
            print(err)

    def refresh_views(self):
        self.keys_view.setModel(self.keys_model)
        self.files_view.setModel(self.files_model)

        keys_head = self.keys_view.horizontalHeader()
        keys_head.setStretchLastSection(False)
        keys_head.setSectionResizeMode(0, QHeaderView.Fixed)
        keys_head.resizeSections(QHeaderView.ResizeToContents)

        files_head = self.files_view.header()
        files_head.setStretchLastSection(False)
        files_head.setSectionResizeMode(0, QHeaderView.Fixed)
        self.files_view.expandAll()
        files_head.resizeSections(QHeaderView.ResizeToContents)
        self.files_view.collapseAll()

    def populate_header_menu(self):
        self.header_menu.clear()

        def toggle_field(field):
            def func(checked):
                keys_args = list(map(
                    lambda x: x[0], self.keys_model.headers))
                keys_index = list(keys_args).index(field)
                keys_header = self.keys_view.horizontalHeader()
                keys_header.setSectionHidden(keys_index, not checked)

                files_args = list(map(
                    lambda x: x[0], self.files_model.headers))
                files_index = files_args.index(field)
                files_header = self.files_view.header()
                files_header.setSectionHidden(files_index, not checked)
            return func

        def toggle_field_action(arg, field):
            action = QAction(
                field, self,
                triggered=toggle_field(arg),
                checkable=True,
            )
            action.setChecked(True)
            return action

        default_fields = ['file', 'key']
        file = self.files_model.headers[0]
        key = self.keys_model.headers[0]
        headers = self.files_model.headers[1:] \
                  + self.keys_model.headers[1:]
        headers = [file, key] + sorted(set(headers))

        for arg, field in headers:
            action = toggle_field_action(arg, field)
            if arg in default_fields:
                action.setDisabled(True)
            else:
                action.trigger()
            self.header_menu.addAction(action)
        self.header_menu.setDisabled(False)

    def open_directory(self):
        dir_name = QFileDialog.getExistingDirectory(self)
        if dir_name:
            self.load_repository(dir_name)


class GitAnnex:
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self._process = self.start()

    def start(self):
        process = subprocess.Popen(
            ["git", "annex", "metadata", "--batch", "--json"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=self.repo_path,
        )
        return process

    def query(self, **query):
        while not (self._process and self._process.poll() is None):
            print('Restarting metadata...')
            self._process = self.start()
        json_ = json.dumps(query)
        print(json_, file=self._process.stdin, flush=True)
        response = self._process.stdout.readline()
        return json.loads(response)

    def metadata(self, all=False):
        jsons = subprocess.check_output(
            ('git', 'annex', 'metadata', '--json',
             '--all' if all else ''),
            universal_newlines=True, cwd=self.repo_path,
        ).splitlines()
        return [json.loads(json_) for json_ in jsons]

    def keys(self):
        return {meta['key'] for meta in self.metadata(all=True)}

    def files(self):
        return {meta['file'] for meta in self.metadata()}

    def item(self, key=None, path=None):
        if key:
            return GitAnnexItem(self, key, file=path)
        elif path:
            key = self.query(file=path)['key']
            return GitAnnexItem(self, key, file=path)
        else:
            raise ValueError('Requires path or key')

    def __repr__(self):
        return 'GitAnnex(repo_path={!r})'.format(self.repo_path)


class GitAnnexItem(collections.abc.MutableMapping):
    def __init__(self, annex, key, file=None):
        self.key = key
        self.file = file
        self.query = partial(annex.query, key=key)

    def fields(self, **fields):
        if not fields:
            return self.query()['fields']
        else:
            return self.query(fields=fields)['fields']

    def __getitem__(self, meta_key):
        if meta_key == 'key':
            return [self.key]
        if meta_key == 'file':
            return [self.file]
        values = self.fields().get(meta_key, [])
        return values

    def __setitem__(self, meta_key, value):
        self.fields(**{meta_key: value})

    def __delitem__(self, meta_key):
        self.fields(**{meta_key: []})

    def __contains__(self, meta_key):
        return meta_key in self.fields()

    def __iter__(self):
        for field in self.fields().keys():
            if not field.endswith('lastchanged'):
                yield field

    def __len__(self):
        len([x for x in self])

    def __eq__(self, other):
        try:
            return self.key == other.key
        except AttributeError:
            return False

    def __hash__(self):
        return hash(('GitAnnexItem', self.key, self.file))

    def __repr__(self):
        return 'GitAnnexItem(key={!r}, file={!r})'.format(
            self.key, self.file)


class GitAnnexParsedItem(GitAnnexItem):
    def __new__(cls, parent, in_parser=None, out_parser=None):
        self = parent.__class__.__new__(parent.__class__)
        self.__dict__.update(parent.__dict__)
        self.__class__ = cls
        return self

    def __init__(self, parent, parse=None, format=None):
        self.parse = parse
        self.format = format

    def __getitem__(self, meta_key):
        value = super().__getitem__(meta_key)
        if callable(self.format):
            value = self.format(value)
        return value

    def __setitem__(self, meta_key, value):
        if callable(self.parse):
            value = self.parse(value)
        return super().__setitem__(meta_key, value)

    def __repr__(self):
        return 'GitAnnexParsedItem(key={!r}, file={!r}, ' \
               'parse={!r}, format={!r})'.format(
                self.key, self.file, self.parse, self.format)

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

    @classmethod
    def collapsed(cls, item):
        return cls(item, cls.collapsed_parse, cls.collapsed_format)

    @classmethod
    def jsonized(cls, item):
        return cls(item, json.loads, json.dumps)


class GitAnnexKeysModel(QAbstractTableModel):
    def __init__(self, repo_path):
        super().__init__()
        self.annex = GitAnnex(repo_path)
        self.headers = [('key', 'Git-Annex Key')]

        self.keys = list(self.annex.keys())
        self.items = [self.annex.item(key) for key in self.keys]

        metadata = self.annex.metadata(all=True)
        fields = [meta.get('fields', {}) for meta in metadata]
        if fields:
            field_names = sorted(set.union(*map(set, fields)))
            for name in field_names:
                if not name.endswith('lastchanged'):
                    self.headers.append((name, name.title()))

    def rowCount(self, parent=QModelIndex(), *args, **kwargs):
        if parent.isValid():
            return 0
        return len(self.items)

    def columnCount(self, parent=QModelIndex(), *args, **kwargs):
        if parent.isValid():
            return 0
        return len(self.headers)

    def data(self, index, role=None):
        if not index.isValid():
            return None

        row, column = index.row(), index.column()
        item = self.items[row]
        arg = self.headers[column][0]

        if role == Qt.UserRole:
            return item[arg]
        elif role == Qt.DisplayRole:
            return GitAnnexParsedItem.collapsed(item)[arg]
        elif role == Qt.ToolTipRole:
            if len(item[arg]) > 1:
                return GitAnnexParsedItem.jsonized(item)[arg]

    def headerData(self, column, orientation=None, role=None):
        if orientation != Qt.Horizontal:
            return None
        if role == Qt.DisplayRole:
            return self.headers[column][1]

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def sort(self, column, sort_order=None):
        def sort_key(item):
            arg = self.headers[column][0]
            value = item[arg]
            if isinstance(value, list):
                return -len(value), (value[-1] if value else '')
            else:
                return value

        self.layoutAboutToBeChanged.emit()
        self.items[:] = sorted(
            self.items, key=sort_key,
            reverse=(sort_order == Qt.DescendingOrder),
        )
        self.layoutChanged.emit()

    def __repr__(self):
        return 'GitAnnexKeysModel(repo_path={!r}, items={!r})'.format(
            self.annex.repo_path, self.items)


class GitAnnexFilesModel(QAbstractItemModel):
    def __init__(self, repo_path):
        super().__init__()
        self.annex = GitAnnex(repo_path)
        self.headers = [('file', 'Filename')]
        self.tree = Tree()

        metadata = self.annex.metadata(all=True)
        fields = [meta.get('fields', {}) for meta in metadata]
        if fields:
            field_names = sorted(set.union(*map(set, fields)))
            for name in field_names:
                if not name.endswith('lastchanged'):
                    self.headers.append((name, name.title()))

        for meta in self.annex.metadata():
            file, key = meta['file'], meta['key']
            parent_dir = os.path.dirname(file)
            self.tree.add(parent_dir, self.annex.item(key, file))

        for dir_ in self.tree.parents():
            while dir_:
                parent = os.path.dirname(dir_)
                self.tree.add(parent, dir_)
                dir_, parent = parent, os.path.dirname(parent)

    def rowCount(self, parent=QModelIndex(), *args, **kwargs):
        if parent.isValid():
            return len(self.tree.children(parent.internalPointer()))
        else:
            return len(self.tree.children(''))

    def columnCount(self, parent=QModelIndex(), *args, **kwargs):
        return len(self.headers)

    def index(self, row, column, parent=QModelIndex(), *args, **kwargs):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        try:
            item = parent.internalPointer() if parent.isValid() else ''
            child = self.tree.children(item)[row]
            return self.createIndex(row, column, child)
        except IndexError:
            return QModelIndex()

    def parent(self, index=QModelIndex()):
        if not index.isValid():
            return QModelIndex()

        try:
            item = index.internalPointer() if index.isValid() else ''
            parent = self.tree.parent(item)
            grand_parent = self.tree.parent(parent)
            parent_row = self.tree.children(grand_parent).index(parent)
            return self.createIndex(parent_row, 0, parent)
        except (IndexError, KeyError):
            return QModelIndex()

    def data(self, index, role=None):
        if not index.isValid():
            return None

        row, column = index.row(), index.column()
        item = index.internalPointer()
        arg = self.headers[column][0]
        value = None

        if isinstance(item, GitAnnexItem):
            if role == Qt.UserRole:
                value = item[arg]
            elif role == Qt.DisplayRole:
                value = GitAnnexParsedItem.collapsed(item)[arg]
                if arg == 'file':
                    value = os.path.basename(value)
            elif role == Qt.ToolTipRole:
                if len(item[arg]) > 1:
                    value = GitAnnexParsedItem.jsonized(item)[arg]
                elif arg == 'file':
                    file = GitAnnexParsedItem.collapsed(item)[arg]
                    if file != os.path.basename(file):
                        value = file
            elif role == Qt.DecorationRole:
                if arg == 'file':
                    icon_type = QFileIconProvider.File
                    value = QFileIconProvider().icon(icon_type)

        elif arg == 'file':
            if role == Qt.UserRole:
                value = item
            elif role == Qt.DisplayRole:
                value = os.path.basename(item)
            elif role == Qt.ToolTipRole:
                value = item
            elif role == Qt.DecorationRole:
                icon_type = QFileIconProvider.Folder
                value = QFileIconProvider().icon(icon_type)

        return value

    def headerData(self, column, orientation=None, role=None):
        if orientation != Qt.Horizontal:
            return None
        if role == Qt.DisplayRole:
            return self.headers[column][1]

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        item = index.internalPointer()
        if isinstance(item, GitAnnexItem):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled

    def sort(self, column, sort_order=Qt.AscendingOrder):
        arg = self.headers[column][0]

        def sort_key(item):
            if isinstance(item, GitAnnexItem):
                value = item[arg]
                return -len(value), (value[-1] if value else '')
            elif item and arg == 'file':
                return -1, item
            else:
                return 0, ''

        self.layoutAboutToBeChanged.emit()
        self.tree.sort(
            key=sort_key,
            reverse=(sort_order == Qt.DescendingOrder)
        )
        self.layoutChanged.emit()

    def __repr__(self):
        return 'GitAnnexFilesModel(repo_path={!r}, tree={!r})'.format(
            self.annex.repo_path, self.tree)


class Tree:
    def __init__(self):
        self._child_to_parent = {}
        self._parent_to_children = defaultdict(list)

    def add(self, parent, *children):
        children = list(filter(
            lambda c: c not in self._parent_to_children[parent],
            children
        ))

        self._parent_to_children[parent].extend(children)
        self._child_to_parent.update({c: parent for c in children})

    def remove(self, parent, child):
        if self._child_to_parent[child] == parent:
            del self._child_to_parent[child]
        if child in self._parent_to_children[parent]:
            self._parent_to_children[parent].remove(child)

    def parent(self, child):
        return self._child_to_parent[child]

    def parents(self):
        return list(self._parent_to_children)

    def children(self, parent):
        return self._parent_to_children[parent]

    def sort(self, key=None, reverse=None):
        for parent, children in self._parent_to_children.items():
            children[:] = sorted(
                sorted(children, key=key, reverse=reverse),
                key=lambda x: not isinstance(x, str)
            )

    def __repr__(self):
        return 'Tree(c2p={!r}, p2c={!r})'.format(
            self._child_to_parent, self._parent_to_children)

if __name__ == '__main__':
    main()