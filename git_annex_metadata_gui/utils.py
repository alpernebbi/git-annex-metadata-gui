#!/usr/bin/env python3

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

import ast
import functools
import time

from PyQt5 import Qt
from PyQt5 import QtGui
from PyQt5 import QtCore

def parse_as_set(x):
    if x == '{}':
        return set()

    try:
        xs = ast.literal_eval(x)
        assert isinstance(xs, set)
        return xs

    except Exception as err:
        fmt = "Can't interpret '{}' as a set."
        msg = fmt.format(x)
        raise ValueError(msg) from err


def automatically_consumed(function):
    generator = None

    @functools.wraps(function)
    def wrapper(instance):
        nonlocal generator
        if generator is None:
            generator = function(instance)

        try:
            endtime = time.monotonic() + 0.1
            while time.monotonic() < endtime:
                next(generator)

        except StopIteration:
            generator = None

        else:
            QtCore.QMetaObject.invokeMethod(
                instance, function.__name__,
                Qt.Qt.QueuedConnection,
            )

    return wrapper


class DataProxyItem(QtGui.QStandardItem):
    def __init__(self, item):
        super().__init__()
        self._item = item

        model = self._item.model()
        model.dataChanged.connect(self._propagate_changes)

    def type(self):
        return QtGui.QStandardItem.UserType + 3

    def data(self, role=Qt.Qt.DisplayRole):
        return self._item.data(role=role)

    def setData(self, value, role=Qt.Qt.EditRole):
        return self._item.setData(value, role=role)

    def flags(self):
        return self._item.flags()

    def _propagate_changes(self, topLeft, bottomRight, roles):
        rows = range(topLeft.row(), bottomRight.row() + 1)
        columns = range(topLeft.column(), bottomRight.column() + 1)

        if self._item.row() in rows and self._item.column() in columns:
            self.emitDataChanged()

    def __repr__(self):
        return "{name}.{cls}({args})".format(
            name=__name__,
            cls=self.__class__.__name__,
            args=self._item,
        )

