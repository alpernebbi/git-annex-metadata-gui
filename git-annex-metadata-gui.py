#!/usr/bin/env python3

import sys
import subprocess
import json
import re
import os
import collections.abc
from functools import partial
from argparse import Namespace

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
from PyQt5.QtWidgets import QDockWidget
from PyQt5.QtWidgets import QLabel
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

        self.actions = Namespace()
        self.menus = Namespace()
        self.models = Namespace()
        self.views = Namespace()
        self.docks = Namespace()

        self.create_actions()
        self.create_menus()
        self.create_center_widget()
        self.create_docks()
        self.create_statusbar()

    def create_actions(self):
        open_action = QAction(self)
        open_action.setText("Open...")
        open_action.setShortcut(Qt.ControlModifier | Qt.Key_O)
        open_action.setStatusTip("Open an existing directory")
        open_action.triggered.connect(self.open_directory)
        self.actions.open = open_action

        exit_action = QAction(self)
        exit_action.setText("Exit")
        exit_action.setShortcut(Qt.ControlModifier | Qt.Key_Q)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        self.actions.exit = exit_action

    def create_menus(self):
        file_menu = self.menuBar().addMenu('&File')
        file_menu.addAction(self.actions.open)
        file_menu.addAction(self.actions.exit)
        self.menus.file = file_menu

        header_menu = self.menuBar().addMenu('&Header')
        header_menu.setDisabled(True)
        self.menus.header = header_menu

        docks_menu = self.menuBar().addMenu('&Docks')
        self.menus.docks = docks_menu

    def create_center_widget(self):
        tabs_widget = QTabWidget()

        files_view = QTreeView()
        files_view.setSortingEnabled(True)
        tabs_widget.addTab(files_view, 'Files')
        self.views.files = files_view

        keys_view = QTableView()
        keys_view.setSortingEnabled(True)
        keys_view.setSelectionBehavior(keys_view.SelectRows)
        tabs_widget.addTab(keys_view, 'Absent Keys')
        self.views.keys = keys_view

        self.setCentralWidget(tabs_widget)

    def create_docks(self):
        preview = QLabel()
        preview.setAlignment(Qt.AlignCenter | Qt.AlignHCenter)
        preview.setTextFormat(Qt.PlainText)

        preview_dock = QDockWidget('Preview')
        preview_dock.setAllowedAreas(
            Qt.LeftDockWidgetArea
            | Qt.RightDockWidgetArea
        )
        preview_dock.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
        )
        preview_dock.setWidget(preview)

        self.addDockWidget(Qt.RightDockWidgetArea, preview_dock)
        self.menus.docks.addAction(preview_dock.toggleViewAction())
        self.docks.preview = preview_dock

    def create_statusbar(self):
        self.statusBar().showMessage('Ready')

    def open_directory(self):
        dir_name = QFileDialog.getExistingDirectory(self)
        if dir_name:
            self.load_repository(dir_name)

    def load_repository(self, dir_name):
        try:
            self.models.keys = GitAnnexKeysModel(dir_name)
            self.models.files = GitAnnexFilesModel(dir_name)
            self.refresh_views()
            self.populate_header_menu()
        except subprocess.CalledProcessError as err:
            msg = 'Couldn\'t load "{}" as a git-annex repo'
            self.statusBar().showMessage(msg.format(dir_name))
            print(err)

    def refresh_views(self):
        keys_view = self.views.keys
        files_view = self.views.files

        keys_view.setModel(self.models.keys)
        files_view.setModel(self.models.files)

        if not self.models.keys.rowCount():
            self.centralWidget().setTabEnabled(1, False)

        keys_header = keys_view.horizontalHeader()
        keys_header.setStretchLastSection(False)
        keys_header.setSectionResizeMode(0, QHeaderView.Fixed)
        keys_header.resizeSections(QHeaderView.ResizeToContents)

        files_header = files_view.header()
        files_header.setStretchLastSection(False)
        files_header.setSectionResizeMode(0, QHeaderView.Fixed)
        files_view.expandAll()
        files_header.resizeSections(QHeaderView.ResizeToContents)
        files_view.collapseAll()

        keys_view.selectionModel() \
            .selectionChanged.connect(self.update_preview)
        files_view.selectionModel() \
            .selectionChanged.connect(self.update_preview)

    def toggle_header_field(self, field, checked):
        keys_fields = list(zip(*self.models.keys.headers))[0]
        keys_field_index = keys_fields.index(field)
        keys_header = self.views.keys.horizontalHeader()
        keys_header.setSectionHidden(keys_field_index, not checked)

        files_fields = list(zip(*self.models.files.headers))[0]
        files_field_index = files_fields.index(field)
        files_header = self.views.files.header()
        files_header.setSectionHidden(files_field_index, not checked)

    def toggle_header_field_action(self, field, name):
        action = QAction(self)
        action.setText(name)
        action.setCheckable(True)
        action.setChecked(True)
        action.triggered.connect(
            partial(self.toggle_header_field, field)
        )
        return action

    def populate_header_menu(self):
        header_menu = self.menus.header
        header_menu.clear()

        default_fields = ['file', 'key']
        headers = sorted(
            set(self.models.files.headers + self.models.keys.headers),
            key=lambda f: (f[0] not in default_fields, f)
        )

        for field, name in headers:
            action = self.toggle_header_field_action(field, name)
            if field in default_fields:
                action.setDisabled(True)
            else:
                action.trigger()
            header_menu.addAction(action)
        header_menu.setDisabled(False)

    def update_preview(self, selection, _):
        preview = self.docks.preview.widget()
        indexes = selection.indexes()
        if indexes:
            index = indexes[0]
            item = index.model().itemFromIndex(index).item
            preview.setText(item.file or item.key)
        else:
            preview.setText('')


class Process():
    def __init__(self, *batch_command, workdir=None):
        self._command = batch_command
        self._workdir = workdir
        self._process = self.start()

    def start(self):
        process = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=self._workdir,
        )
        return process

    def running(self):
        return self._process and self._process.poll() is None

    def query_json(self, **query):
        json_ = json.dumps(query)
        response = self.query_line(json_)
        return json.loads(response)

    def query_line(self, query):
        while not self.running():
            self._process = self.start()
        print(query, file=self._process.stdin, flush=True)
        return self._process.stdout.readline().strip()


class GitAnnex:
    def __init__(self, repo_path):
        self.repo_path = repo_path

        self.processes = Namespace()
        self.processes.metadata = Process(
            'git', 'annex', 'metadata', '--batch', '--json',
            workdir=self.repo_path
        )
        self.processes.locate = Process(
            'git', 'annex', 'contentlocation', '--batch',
            workdir=self.repo_path
        )

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
            key = self.processes.metadata.query_json(file=path)['key']
            return GitAnnexFile(self, key, file=path)
        else:
            raise ValueError('Requires path or key')

    def locate(self, key, abs=False):
        rel_path = self.processes.locate.query_line(key)
        if abs:
            return os.path.join(self.repo_path, rel_path)
        else:
            return rel_path

    def __repr__(self):
        return 'GitAnnex(repo_path={!r})'.format(self.repo_path)


class GitAnnexFile(collections.abc.MutableMapping):
    def __init__(self, annex, key, file=None):
        self.key = key
        self.file = file
        self.annex = annex
        self.query = partial(
            self.annex.processes.metadata.query_json,
            key=key
        )
        self.locate = partial(self.annex.locate, self.key)

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