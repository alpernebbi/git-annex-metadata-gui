#! /usr/bin/make -f

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

QTUI:=$(wildcard qtdesigner-ui/*.ui)
PYUI:=$(QTUI:qtdesigner-ui/%.ui=git_annex_metadata_gui/%_ui.py)

git_annex_metadata_gui/%_ui.py: qtdesigner-ui/%.ui
	pyuic5 -o $@ $<

all: gui

gui: $(PYUI)

design:
	PYQTDESIGNERPATH=qtdesigner-plugins \
	PYTHONPATH=. \
		designer qtdesigner-ui/main_window.ui \
		>/dev/null 2>&1 &

test:
	python3 -m "unittest" -vb

.PHONY: all gui design test
