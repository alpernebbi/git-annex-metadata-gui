#!/usr/bin/env python3

import sys
import subprocess
import json
import re
import os
import collections.abc
from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QTreeView
from PyQt5.QtWidgets import QTableView
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtWidgets import QFileIconProvider
from PyQt5.QtGui import QStandardItem
from PyQt5.QtGui import QStandardItemModel


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
        self.keys_view.setSortingEnabled(True)
        self.keys_view.setSelectionBehavior(self.keys_view.SelectRows)
        self.view_tabs.addTab(self.keys_view, 'Absent Keys')

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

    def keys(self, absent=False):
        all_keys = {meta['key'] for meta in self.metadata(all=True)}
        if absent:
            file_keys = {meta['key'] for meta in self.metadata()}
            return all_keys - file_keys
        else:
            return all_keys

    def files(self):
        return {meta['file'] for meta in self.metadata()}

    def fields(self):
        metadata = self.metadata(all=True)
        fields = [meta.get('fields', {}) for meta in metadata]
        return filter(
            lambda f: not f.endswith('lastchanged'),
            set.union(*map(set, fields + [{}]))
        )

    def item(self, key=None, path=None):
        if key:
            return GitAnnexFile(self, key, file=path)
        elif path:
            key = self.query(file=path)['key']
            return GitAnnexFile(self, key, file=path)
        else:
            raise ValueError('Requires path or key')

    def __repr__(self):
        return 'GitAnnex(repo_path={!r})'.format(self.repo_path)


class GitAnnexFile(collections.abc.MutableMapping):
    def __init__(self, annex, key, file=None):
        self.key = key
        self.file = file
        self.annex = annex
        self.query = partial(self.annex.query, key=key)

    def _fields(self, **fields):
        if not fields:
            return self.query()['fields']
        else:
            return self.query(fields=fields)['fields']

    def field(self, field):
        return GitAnnexField(self, field)

    def __getitem__(self, meta_key):
        if meta_key == 'key':
            return [self.key]
        if meta_key == 'file':
            return [self.file]
        values = self._fields().get(meta_key, [])
        return values

    def __setitem__(self, meta_key, value):
        self._fields(**{meta_key: value})

    def __delitem__(self, meta_key):
        self._fields(**{meta_key: []})

    def __contains__(self, meta_key):
        return meta_key in self._fields()

    def __iter__(self):
        for field in self._fields().keys():
            if not field.endswith('lastchanged'):
                yield field

    def __len__(self):
        len([x for x in self])

    def __repr__(self):
        return 'GitAnnexFile(key={!r}, file={!r})'.format(
            self.key, self.file)


class GitAnnexField(QStandardItem):
    qt_type = QStandardItem.UserType + 1

    def __init__(self, item, field):
        super().__init__()
        self.item = item
        self.field = field

    @property
    def value(self):
        return self.item[self.field]

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


class GitAnnexKeysModel(QStandardItemModel):
    def __init__(self, repo_path):
        super().__init__()
        self.annex = GitAnnex(repo_path)
        self.headers = [('key', 'Git-Annex Key')]

        fields = sorted(self.annex.fields())
        self.headers.extend((name, name.title()) for name in fields)
        self.setHorizontalHeaderLabels(n for _, n in self.headers)

        items = (
            self.annex.item(key=key)
            for key in self.annex.keys(absent=True)
        )
        for item in items:
            self.appendRow([item.field(f) for f, _ in self.headers])

    def flags(self, index):
        item = self.itemFromIndex(index)
        if isinstance(item, GitAnnexField):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable


class GitAnnexFilesModel(QStandardItemModel):
    def __init__(self, repo_path):
        super().__init__()
        self.annex = GitAnnex(repo_path)
        self.headers = [('file', 'Filename')]

        fields = sorted(self.annex.fields())
        self.headers.extend((name, name.title()) for name in fields)
        self.setHorizontalHeaderLabels(n for _, n in self.headers)

        dir_items = {'': [self.invisibleRootItem()]}

        def make_dir_item(dir_):
            if dir_ in dir_items:
                return dir_items[dir_]
            dir_item = [
                GitAnnexDirectory(dir_, column, field=field)
                for column, (field, _) in enumerate(self.headers)
            ]
            dir_items[dir_] = dir_item
            parent = os.path.dirname(dir_)
            parent_item = make_dir_item(parent)[0]
            parent_item.appendRow(dir_item)
            return dir_item

        files = self.annex.files()
        for dir_ in map(os.path.dirname, files):
            make_dir_item(dir_)

        for file in files:
            item = self.annex.item(path=file)
            parent = dir_items[os.path.dirname(file)][0]
            parent.appendRow(
                [item.field(f) for f, _ in self.headers]
            )

    def flags(self, index):
        item = self.itemFromIndex(index)
        if isinstance(item, GitAnnexDirectory):
            return Qt.ItemIsEnabled
        elif isinstance(item, GitAnnexField):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable


if __name__ == '__main__':
    main()