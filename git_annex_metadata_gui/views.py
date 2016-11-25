from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtWidgets import QTreeView


class GitAnnexView(QTreeView):
    def __init__(self):
        super().__init__()

        self.setSortingEnabled(True)
        self.setSelectionBehavior(self.SelectRows)
        self.setUniformRowHeights(True)

    def setModel(self, model):
        super().setModel(model)

        self.expandAll()
        header = self.header()
        header.setStretchLastSection(False)
        header.resizeSections(QHeaderView.ResizeToContents)
        self.collapseAll()

    def viewportSizeHint(self):
        orig_size = super().viewportSizeHint()
        max_file_length = self.columnWidth(0)
        return QSize(max_file_length * 1.05, orig_size.height())

    def toggle_header_field(self, field, visible):
        fields = list(zip(*self.model().headers))[0]
        field_index = fields.index(field)
        header = self.header()
        header.setSectionHidden(field_index, not visible)
