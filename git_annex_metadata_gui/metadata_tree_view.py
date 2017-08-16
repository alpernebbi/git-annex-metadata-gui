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
from PyQt5 import QtGui
from PyQt5 import QtWidgets

class MetadataTreeView(QtWidgets.QTreeView):
    item_selected = QtCore.pyqtSignal(QtGui.QStandardItem)
    header_visibility_changed = QtCore.pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)

    def setModel(self, model):
        self._bare_model = model
        self._proxy_model = QtCore.QSortFilterProxyModel(model)
        self._proxy_model.setSourceModel(model)
        super().setModel(self._proxy_model)

        signal = self.selectionModel().selectionChanged
        signal.connect(self._on_selection_changed)

    @QtCore.pyqtSlot(str)
    @QtCore.pyqtSlot(str, bool)
    def show_header(self, title, visible=True):
        if title not in self._bare_model.fields:
            return
        idx = self._bare_model.fields.index(title)
        header = self.header()
        if header.isSectionHidden(idx) != (not visible):
            header.setSectionHidden(idx, not visible)
            self.header_visibility_changed.emit(title, visible)

    @QtCore.pyqtSlot(str)
    def hide_header(self, title):
        self.show_header(title, False)

    @QtCore.pyqtSlot(str)
    def create_header(self, title):
        self._bare_model.insert_field(title)

    def _on_selection_changed(self, selected, deselected):
        indexes = selected.indexes()
        if not indexes:
            return

        index = indexes[0]
        src_index = index.model().mapToSource(index)
        item = src_index.model().itemFromIndex(src_index)

        self.item_selected.emit(item)
