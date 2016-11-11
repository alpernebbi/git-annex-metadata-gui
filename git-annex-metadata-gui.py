#!/usr/bin/env python3

import sys
import subprocess
import json
import os
from functools import partial

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

        self.header_menu = self.menuBar().addMenu('&Header')
        self.header_menu.setDisabled(True)

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

    def load_repository(self, dir_name):
        try:
            self.annex_model = GitAnnexMetadataModel(dir_name)
            self.refresh_views()
            self.populate_header_menu()
        except subprocess.CalledProcessError as err:
            msg = 'Couldn\'t load "{}" as a git-annex repo'
            self.statusBar().showMessage(msg.format(dir_name))
            print(err)

    def refresh_views(self):
        self.files_view.setModel(self.annex_model)
        files_index = self.annex_model.index(0, 0)
        self.files_view.setRootIndex(files_index)

        self.keys_view.setModel(self.annex_model)
        keys_index = self.annex_model.index(1, 0)
        self.keys_view.setRootIndex(keys_index)

        name_index = self.annex_model.root.header_order.index('name')
        self.keys_view.header().setSectionHidden(name_index, True)

        key_index = self.annex_model.root.header_order.index('key')
        self.files_view.header().setSectionHidden(key_index, True)

    def populate_header_menu(self):
        self.header_menu.clear()

        def toggle_field(field):
            def func(checked):
                index = self.annex_model.root.header_order.index(field)
                files_header = self.files_view.header()
                files_header.setSectionHidden(index, not checked)
                keys_header = self.keys_view.header()
                keys_header.setSectionHidden(index, not checked)
            return func

        def toggle_field_action(field):
            action = QAction(
                field.title(), self,
                triggered=toggle_field(field),
                checkable=True,
            )
            action.setChecked(True)
            return action

        default_fields = RootNode().header_order
        for field in self.annex_model.root.header_order:
            action = toggle_field_action(field)
            if field in default_fields:
                action.setDisabled(True)
            self.header_menu.addAction(action)
        self.header_menu.setDisabled(False)

    def open_directory(self):
        dir_name = QFileDialog.getExistingDirectory(self)
        if dir_name:
            self.load_repository(dir_name)


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
        self.root = RootNode()

        files = self._files()
        files_root = TreeNode(self.root, name='[files]')

        dirs = set()
        for file in files:
            dir_ = os.path.dirname(file)
            while dir_:
                dirs.add(dir_)
                dir_ = os.path.dirname(dir_)

        dir_items = {}
        for dir_ in sorted(dirs):
            parent = dir_items.get(os.path.dirname(dir_), files_root)
            name = os.path.basename(dir_)
            dir_item = TreeNode(parent, name=name)
            parent.children.append(dir_item)
            dir_items[dir_] = dir_item

        for file in files:
            dir_ = os.path.dirname(file)
            parent = dir_items.get(dir_, files_root)
            file_item = AnnexNode(
                parent=parent,
                query_func=self._metadata_query,
                path=file,
            )
            for field in file_item.data:
                if field not in self.root.header_order:
                    self.root.header_order.append(field)
                    self.root.header_names[field] = field.title()
            parent.children.append(file_item)
        self.root.children.append(files_root)

        keys = self._keys()
        keys_root = TreeNode(self.root, name='[keys]')
        for key in keys:
            item = AnnexNode(
                parent=keys_root,
                query_func=self._metadata_query,
                key=key,
            )
            keys_root.children.append(item)
        self.root.children.append(keys_root)

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index, role=None):
        if not index.isValid():
            return None

        item = index.internalPointer()
        arg = self.root.header_order[index.column()]
        value = item.data.get(arg, None)

        if role == Qt.UserRole:
            return value
        elif role == Qt.DisplayRole:
            if isinstance(value, list):
                if len(value) > 1:
                    return '<{} values>'.format(len(value))
                elif len(value) == 1:
                    return value[0]
                else:
                    return None
            return value

    def headerData(self, section, orientation, role=None):
        if orientation != Qt.Horizontal:
            return None
        if role != Qt.DisplayRole:
            return None

        arg = self.root.header_order[section]
        return self.root.header_names[arg]

    def rowCount(self, parent=QModelIndex(), *args, **kwargs):
        if parent.isValid():
            item = parent.internalPointer()
        else:
            item = self.root

        return len(item.children)

    def columnCount(self, parent=QModelIndex(), *args, **kwargs):
        return len(self.root.header_order)

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


class TreeNode:
    def __init__(self, parent, **kwargs):
        self.data = kwargs
        self.parent = parent
        self.children = []

    def __repr__(self):
        repr_ = "TreeNode(data={!r}, children={!r})"
        return repr_.format(self.data, self.children)


class RootNode(TreeNode):
    def __init__(self):
        super().__init__(None)
        self.header_order = [
            'name',
            'key',
        ]
        self.header_names = {
            'name': 'Filename',
            'key': 'Git-Annex Key',
        }


class AnnexNode(TreeNode):
    def __init__(self, parent, query_func, key=None, path=None):
        super().__init__(parent)

        if key:
            self._query = partial(query_func, key=key)
        elif path:
            self._query = partial(query_func, file=path)
        else:
            raise KeyError('Requires path or key')

    @property
    def data(self):
        metadata = self._query()

        data_ = {k: v for k, v in metadata['fields'].items()
                 if not k.endswith('lastchanged')}

        data_['key'] = metadata['key']
        if metadata['file']:
            data_['path'] = metadata['file']
            data_['name'] = os.path.basename(metadata['file'])
        else:
            data_['path'] = None
            data_['name'] = None
        return data_

    @data.setter
    def data(self, value):
        try:
            self._query(fields=value)
        except AttributeError:
            pass

    def __repr__(self):
        return "AnnexNode(data={!r})".format(self.data)

if __name__ == '__main__':
    main()