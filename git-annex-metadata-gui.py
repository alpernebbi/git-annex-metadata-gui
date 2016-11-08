#!/usr/bin/env python3

import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QFileSystemModel
from PyQt5.QtWidgets import QTreeView


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
        self.exit_action = QAction(
            "Exit", self,
            shortcut="Ctrl+Q",
            statusTip="Exit the application",
            triggered=self.close,
        )

    def create_menus(self):
        self.file_menu = self.menuBar().addMenu('&File')
        self.file_menu.addAction(self.exit_action)

    def create_center_widget(self):
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath('/tmp')

        self.fs_view = QTreeView()
        self.fs_view.setModel(self.fs_model)
        self.fs_view.setRootIndex(self.fs_model.index('/tmp'))
        self.fs_view.setSortingEnabled(True)

        self.setCentralWidget(self.fs_view)

    def create_statusbar(self):
        self.statusBar().showMessage('Ready')

if __name__ == '__main__':
    main()