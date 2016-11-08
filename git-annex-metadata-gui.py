#!/usr/bin/env python3

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QMainWindow


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


if __name__ == '__main__':
    main()