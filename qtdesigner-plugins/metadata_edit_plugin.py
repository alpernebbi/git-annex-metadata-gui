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

import bisect

from PyQt5 import Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5 import QtDesigner

from metadata_edit import MetadataEdit

class MetadataEditPlugin(QtDesigner.QPyDesignerCustomWidgetPlugin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._models = []
        self._initialized = False

    def initialize(self, formEditor):
        self._initialized = True

    def isInitialized(self):
        return self._initialized

    def createWidget(self, parent):
        model = MockMetadataModel()
        self._models.append(model)
        key_item = model.item(0, 0)
        return MetadataEdit(key_item, parent)

    def name(self):
        return "MetadataEdit"

    def group(self):
        return "Git-Annex Metadata Gui Widgets"

    def icon(self):
        return QtGui.QIcon()

    def toolTip(self):
        return ""

    def whatsThis(self):
        return ""

    def isContainer(self):
        return False

    def includeFile(self):
        return "metadata_edit"

    def domXml(self):
        cls = self.name()
        name = self.name()
        xml = '<widget class="{}" name="{}"></widget>'
        return xml.format(cls, name)


class MockMetadataModel(QtGui.QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        item = MockKeyItem('SHA256E-s0--0')
        self.appendRow(item)

        self.fields = ['Git-Annex Key']
        self.setHorizontalHeaderLabels(self.fields)

        for field in ['baz', 'diz']:
            self.insert_field(field)

    @QtCore.pyqtSlot(str)
    def insert_field(self, field):
        if field in self.fields:
            return
        col = bisect.bisect(self.fields, field, lo=1)
        self.fields.insert(col, field)
        self.insertColumn(col, [MockFieldItem()])
        self.setHorizontalHeaderLabels(self.fields)


class MockKeyItem(QtGui.QStandardItem):
    def __init__(self, text):
        super().__init__(text)

    @property
    def key(self):
        return self.text()


class MockFieldItem(QtGui.QStandardItem):
    def __init__(self):
        super().__init__()
        self._set = {'foo', 'bar'}

    def data(self, role=Qt.Qt.DisplayRole):
        if role == Qt.Qt.UserRole:
            return self._set
        else:
            return super().data(role=role)

    def setData(self, value, role=Qt.Qt.DisplayRole):
        if role == Qt.Qt.UserRole:
            self._set = set(value)
            self.emitDataChanged()
        else:
            super().setData(value, role=role)

