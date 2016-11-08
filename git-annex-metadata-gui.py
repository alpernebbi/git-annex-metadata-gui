#!/usr/bin/env python3

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QAction


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

        self.exit_action = QAction(
            "Exit", self,
            shortcut="Ctrl+Q",
            statusTip="Exit the application",
            triggered=self.close,
        )

        self.file_menu = self.menuBar().addMenu('&File')
        self.file_menu.addAction(self.exit_action)

        self.statusBar().showMessage('Ready')

if __name__ == '__main__':
    main()