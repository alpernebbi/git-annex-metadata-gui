# Git-Annex-Metadata-Gui
# Copyright (C) 2017 Alper Nebi Yasak
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from PyQt5 import QtCore
from PyQt5 import QtWidgets

class AutoSizeLineEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.updateGeometry)

    def sizeHint(self):
        height = super().sizeHint().height()
        min_width = self.minimumSizeHint().width()
        text_width = self.fontMetrics().width(self.text())
        return QtCore.QSize(text_width + min_width, height)

