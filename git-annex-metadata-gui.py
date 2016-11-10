#!/usr/bin/env python3

import sys
import subprocess
import json
import os
from functools import partialmethod

from PyQt5.QtCore import Qt
from PyQt5.QtCore import QAbstractItemModel
from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QTreeView
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QTabWidget


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
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

    def create_center_widget(self):
        self.view_tabs = QTabWidget()

        self.files_view = QTreeView()
        self.files_view.setSortingEnabled(True)
        self.view_tabs.addTab(self.files_view, 'Files')

        self.keys_view = QTreeView()
        self.keys_view .setSortingEnabled(True)
        self.view_tabs.addTab(self.keys_view, 'Keys')

        self.setCentralWidget(self.view_tabs)

    def create_statusbar(self):
        self.statusBar().showMessage('Ready')

    def open_directory(self):
        dir_name = QFileDialog.getExistingDirectory()
        if dir_name:
            try:
                self.annex_model = GitAnnexMetadataModel(dir_name)

                self.files_view.setModel(self.annex_model)
                files_index = self.annex_model.index(0, 0)
                self.files_view.setRootIndex(files_index)

                self.keys_view.setModel(self.annex_model)
                keys_index = self.annex_model.index(1, 0)
                self.keys_view.setRootIndex(keys_index)
            except RuntimeError as e:
                print(e)


class GitAnnexMetadataModel(QAbstractItemModel):
    def __init__(self, repo_path):
        super().__init__()
        self.repo_path = repo_path
        self._metadata = None
        self._metadata_start()
        self._root = None
        self._create_tree()

    def _metadata_start(self):
        self._metadata = subprocess.Popen(
            ["git", "annex", "metadata", "--batch", "--json"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=self.repo_path,
        )

    def _metadata_query(self, **query):
        while not (self._metadata and self._metadata.poll() is None):
            print('Restarting metadata...')
            self._metadata_start()
        json_ = json.dumps(query)
        print(json_, file=self._metadata.stdin, flush=True)
        response = self._metadata.stdout.readline()
        return json.loads(response)

    def _keys(self):
        jsons = subprocess.check_output(
            ('git', 'annex', 'metadata', '--all', '--json'),
            universal_newlines=True, cwd=self.repo_path,
        ).splitlines()
        meta_list = [json.loads(json_) for json_ in jsons]
        return {meta['key'] for meta in meta_list}

    def _files(self):
        jsons = subprocess.check_output(
            ('git', 'annex', 'metadata', '--json'),
            universal_newlines=True, cwd=self.repo_path,
        ).splitlines()
        meta_list = [json.loads(json_) for json_ in jsons]
        return {meta['file'] for meta in meta_list}

    def _create_tree(self):
        self.root = GitAnnexDirectoryItem(None, None)
        files = self._files()
        files_root = GitAnnexDirectoryItem('[files]', self.root)

        dirs = set()
        for file in files:
            dir_ = os.path.dirname(file)
            while dir_:
                dirs.add(dir_)
                dir_ = os.path.dirname(dir_)

        dir_items = {}
        for dir_ in sorted(dirs):
            parent = dir_items.get(os.path.dirname(dir_), files_root)
            dir_item =  GitAnnexDirectoryItem(dir_, parent)
            parent.add_child(dir_item)
            dir_items[dir_] = dir_item

        for file in files:
            dir_ = os.path.dirname(file)
            parent = dir_items.get(dir_, files_root)
            file_item = GitAnnexMetadataItem(
                parent=parent,
                query_func=self._metadata_query,
                path=file,
            )
            parent.add_child(file_item)
        self.root.add_child(files_root)

        keys = self._keys()
        keys_root = GitAnnexDirectoryItem('[keys]', self.root)
        for key in keys:
            item = GitAnnexMetadataItem(
                parent=keys_root,
                query_func=self._metadata_query,
                key=key,
            )
            keys_root.add_child(item)
        self.root.add_child(keys_root)

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index, role=None):
        if not index.isValid():
            return None
        if role != Qt.DisplayRole:
            return None

        item = index.internalPointer()

        if isinstance(item, GitAnnexDirectoryItem):
            return item.path
        elif isinstance(item, GitAnnexMetadataItem):
            try:
                return item.key
            except:
                return item.path
        else:
            return None

    def headerData(self, section, orientation, role=None):
        if orientation != Qt.Horizontal:
            return None
        if role != Qt.DisplayRole:
            return None

        if section == 0:
            return 'Path'
        else:
            return None

    def rowCount(self, parent=QModelIndex(), *args, **kwargs):
        if parent.isValid():
            item = parent.internalPointer()
        else:
            item = self.root

        if isinstance(item, GitAnnexDirectoryItem):
            return len(item.children)
        else:
            return 0

    def columnCount(self, parent=QModelIndex(), *args, **kwargs):
        return 1

    def index(self, row, column, parent=QModelIndex(), *args, **kwargs):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if parent.isValid():
            item = parent.internalPointer()
        else:
            item = self.root

        try:
            child = item.children[row]
            return self.createIndex(row, column, child)
        except:
            return QModelIndex()

    def parent(self, index=QModelIndex()):
        if not index.isValid():
            return QModelIndex()

        child = index.internalPointer()
        parent = child.parent

        if parent == self.root:
            return QModelIndex()

        parent_row = parent.parent.children.index(parent)
        return self.createIndex(parent_row, 0, parent)


class GitAnnexDirectoryItem:
    def __init__(self, path, parent):
        self.path = path
        self.parent = parent
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def __repr__(self):
        repr_ = "GitAnnexDirectoryItem(path={!r}, children={!r})"
        return repr_.format(self.path, self.children)


class GitAnnexMetadataItem:
    def __init__(self, parent, query_func, key=None, path=None):
        self.parent = parent

        if key:
            self.key = key
            self.query = partialmethod(query_func, key=self.key)
        elif path:
            self.path = path
            self.query = partialmethod(query_func, file=self.path)
        else:
            raise KeyError('Requires path or key')

    def __repr__(self):
        try:
            return "GitAnnexMetadataItem(key={!r})".format(self.key)
        except:
            return "GitAnnexMetadataItem(path={!r})".format(self.path)

if __name__ == '__main__':
    main()