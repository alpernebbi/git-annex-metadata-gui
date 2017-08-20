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

import logging

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

logger = logging.getLogger(__name__)


class MetadataTableView(QtWidgets.QTableView):
    item_selected = QtCore.pyqtSignal(QtGui.QStandardItem)
    header_visibility_changed = QtCore.pyqtSignal(str, bool)
    header_created = QtCore.pyqtSignal(str)
    model_reset = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fields = []
        self._filter = ('', 'Fixed')

    def setModel(self, model):
        self._bare_model = model
        self._proxy_model = QtCore.QSortFilterProxyModel(model)
        self._proxy_model.setSourceModel(model)
        super().setModel(self._proxy_model)

        signal = self.selectionModel().selectionChanged
        signal.connect(self._on_selection_changed)

        signal = self._bare_model.headerDataChanged
        signal.connect(self._on_header_data_changed)

        signal = self._bare_model.modelReset
        signal.connect(self._on_model_reset)

    @QtCore.pyqtSlot(str)
    @QtCore.pyqtSlot(str, bool)
    def show_header(self, title, visible=True):
        if title not in self._bare_model.fields:
            return
        idx = self._bare_model.fields.index(title)
        header = self.horizontalHeader()
        if header.isSectionHidden(idx) != (not visible):
            header.setSectionHidden(idx, not visible)
            self.header_visibility_changed.emit(title, visible)

        fmt = "{} table column for field '{}'."
        msg = fmt.format('Showing' if visible else 'Hiding', title)
        logger.info(msg)

    @QtCore.pyqtSlot(str)
    def hide_header(self, title):
        self.show_header(title, False)

    @QtCore.pyqtSlot(str)
    def create_header(self, title):
        self._bare_model.insert_field(title)

    @QtCore.pyqtSlot(str)
    def set_filter_pattern(self, filter_pattern):
        self._filter = (filter_pattern, self._filter[1])
        self.filter()

    @QtCore.pyqtSlot(str)
    def set_filter_type(self, filter_type):
        self._filter = (self._filter[0], filter_type)
        self.filter()

    def filter(self):
        pattern, type_ = self._filter

        if not self.model():
            return

        if type_ == 'Fixed':
            self.model().setFilterFixedString(pattern)
        elif type_ == 'Regex':
            self.model().setFilterRegExp(pattern)
        elif type_ == 'Wildcard':
            self.model().setFilterWildcard(pattern)

        if pattern:
            fmt = "Filtered keys with {} pattern '{}'."
            msg = fmt.format(type_, pattern)
        else:
            msg = "Removed key filter."
        logger.info(msg)

    def _on_selection_changed(self, selected, deselected):
        indexes = selected.indexes()
        if not indexes:
            return

        index = indexes[0]
        src_index = index.model().mapToSource(index)
        item = src_index.model().itemFromIndex(src_index)

        self.item_selected.emit(item)

    def _on_header_data_changed(self, orientation, first, last):
        fields = self._bare_model.fields[1:]

        for field in fields:
            if field not in self._fields:
                self.header_created.emit(field)

        self._fields = fields

    def _on_model_reset(self):
        self._fields = []
        self.model_reset.emit()
