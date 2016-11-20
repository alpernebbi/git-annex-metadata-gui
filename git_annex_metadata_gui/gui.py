#!/usr/bin/env python3

import subprocess
import sys
from argparse import Namespace
from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QTabWidget

from git_annex_metadata_gui.models import GitAnnexWrapper
from git_annex_metadata_gui.models import GitAnnexFilesModel
from git_annex_metadata_gui.models import GitAnnexKeysModel
from git_annex_metadata_gui.views import GitAnnexFilesView
from git_annex_metadata_gui.views import GitAnnexKeysView
from git_annex_metadata_gui.docks import MetadataEditorDock
from git_annex_metadata_gui.docks import PreviewDock


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

        self.setWindowTitle('Git Annex Metadata Editor')

        self.current_dir = None
        self.annex = None

        self.actions = Namespace()
        self.menus = Namespace()
        self.models = Namespace()
        self.views = Namespace()
        self.docks = Namespace()

        self.create_actions()
        self.create_menus()
        self.create_views()
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

        refresh_action = QAction(self)
        refresh_action.setText("Refresh")
        refresh_action.setShortcut(Qt.Key_F5)
        refresh_action.setStatusTip("Reload files and keys")
        refresh_action.triggered.connect(self.refresh_all)
        refresh_action.setDisabled(True)
        self.actions.refresh = refresh_action

        exit_action = QAction(self)
        exit_action.setText("Exit")
        exit_action.setShortcut(Qt.ControlModifier | Qt.Key_Q)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        self.actions.exit = exit_action

    def create_menus(self):
        file_menu = self.menuBar().addMenu('&File')
        file_menu.addAction(self.actions.open)
        file_menu.addAction(self.actions.refresh)
        file_menu.addAction(self.actions.exit)
        self.menus.file = file_menu

        header_menu = self.menuBar().addMenu('&Header')
        header_menu.setDisabled(True)
        self.menus.header = header_menu

        docks_menu = self.menuBar().addMenu('&Docks')
        self.menus.docks = docks_menu

    def create_views(self):
        self.views.files = GitAnnexFilesView()
        self.views.keys = GitAnnexKeysView()

    def create_center_widget(self):
        tabs_widget = QTabWidget()
        tabs_widget.addTab(self.views.files, 'Files')
        tabs_widget.addTab(self.views.keys, 'Absent Keys')
        self.setCentralWidget(tabs_widget)

    def create_docks(self):
        preview_dock = PreviewDock()
        self.addDockWidget(Qt.RightDockWidgetArea, preview_dock)
        self.menus.docks.addAction(preview_dock.toggleViewAction())
        self.docks.preview = preview_dock

        editor_dock = MetadataEditorDock(self.create_new_field)
        self.tabifyDockWidget(preview_dock, editor_dock)
        self.menus.docks.addAction(editor_dock.toggleViewAction())
        self.docks.editor = editor_dock

    def create_statusbar(self):
        self.statusBar().showMessage('Ready')

    def open_directory(self):
        dir_name = QFileDialog.getExistingDirectory(self)
        if dir_name:
            self.load_repository(dir_name)

    def refresh_all(self):
        self.docks.preview.set_item(None)
        self.docks.editor.set_item(None)
        self.load_repository(self.current_dir)

    def load_repository(self, dir_name):
        try:
            self.annex = GitAnnexWrapper(dir_name)
        except subprocess.CalledProcessError as err:
            if 'Not a git repository' in err.stderr:
                msg = "{} isn't in a git repository."
            elif 'First run: git-annex init' in err.stderr:
                msg = "{} isn't in a git-annex repository."
            else:
                raise
            self.statusBar().showMessage(msg.format(dir_name))
            return
        except FileNotFoundError as err:
            self.statusBar().showMessage(err.args[1])
            return

        self.models.keys = GitAnnexKeysModel(self.annex)
        self.models.files = GitAnnexFilesModel(self.annex)

        self.current_dir = dir_name
        self.actions.refresh.setDisabled(False)
        self.refresh_views()
        self.populate_header_menu()

    def refresh_views(self):
        keys_view = self.views.keys
        files_view = self.views.files

        keys_view.setModel(self.models.keys)
        files_view.setModel(self.models.files)

        self.centralWidget() \
            .setTabEnabled(0, self.models.files.rowCount())
        self.centralWidget() \
            .setTabEnabled(1, self.models.keys.rowCount())

        keys_view.selectionModel() \
            .selectionChanged.connect(self.selection_updated)
        files_view.selectionModel() \
            .selectionChanged.connect(self.selection_updated)

    def toggle_header_field_action(self, field, name):
        action = QAction(self)
        action.setText(name)
        action.setCheckable(True)
        action.setChecked(True)
        action.triggered.connect(
            partial(self.views.keys.toggle_header_field, field)
        )
        action.triggered.connect(
            partial(self.views.files.toggle_header_field, field)
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

    def selection_updated(self, selected, deselected):
        indexes = selected.indexes()
        if indexes:
            index = indexes[0]
            item = index.model().itemFromIndex(index).item
        else:
            item = None

        self.docks.preview.set_item(item)
        self.docks.editor.set_item(item)

    def create_new_field(self, field):
        files_model = self.models.files
        keys_model = self.models.keys
        headers = (*files_model.headers, *keys_model.headers)
        fields = (f for f, _ in headers)

        if field in fields:
            return

        keys_model.new_field(field)
        files_model.new_field(field)
        action = self.toggle_header_field_action(field, field.title())
        action.trigger()
        self.menus.header.addAction(action)


if __name__ == '__main__':
    main()
