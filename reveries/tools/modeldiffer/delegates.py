
from avalon.vendor.Qt import QtWidgets, QtCore
from . import models, lib


class DiffDelegate(QtWidgets.QStyledItemDelegate):

    ICON_SIZE = 16
    ICON_MARGIN = 6
    ICON_COUNT = 4
    ICON_SPACE = ICON_SIZE * ICON_COUNT + ICON_MARGIN * (ICON_COUNT + 1)

    ID_ICONS = [
        ("hashtag", "#6A6A6A"),  # Not Match
        ("hashtag", "#A290B9"),  # Match By Id, & 2
    ]

    NAME_ICONS = [
        ("align-left", "#6A6A6A"),  # Not Match
        ("align-left", "#A290B9"),  # Match By Name, & 1
    ]

    POINTS_ICONS = [
        ("cube", "#EC534E"),  # Point Not Match
        ("cube", "#38DB8C"),  # Point Ok
        ("cube", "#6A6A6A"),  # Point Dimmed (Item not matched)
    ]

    UVMAP_ICONS = [
        ("delicious", "#EC534E"),  # UV Not Match
        ("delicious", "#38DB8C"),  # UV Ok
        ("delicious", "#6A6A6A"),  # UV Dimmed (Item not matched)
    ]

    DiffStateRole = models.ComparerModel.DiffStateRole

    def __init__(self, parent=None):
        super(DiffDelegate, self).__init__(parent)

        s = (self.ICON_SIZE, self.ICON_SIZE)

        self.name_pixmap = [
            lib.icon(n, c).pixmap(*s) for n, c in self.NAME_ICONS
        ]
        self.id_pixmap = [
            lib.icon(n, c).pixmap(*s) for n, c in self.ID_ICONS
        ]
        self.points_pixmap = [
            lib.icon(n, c).pixmap(*s) for n, c in self.POINTS_ICONS
        ]
        self.uvmap_pixmap = [
            lib.icon(n, c).pixmap(*s) for n, c in self.UVMAP_ICONS
        ]

    def sizeHint(self, option, index):
        size = option.rect.size()
        size.setWidth(self.ICON_SPACE)
        return size

    def paint(self, painter, option, index):
        # super(DiffDelegate, self).paint(painter, option, index)

        states = index.data(self.DiffStateRole)
        name_state, points_state, uvmap_state = states

        pixmaps = [
            self.id_pixmap[bool(name_state & 2)],
            self.name_pixmap[bool(name_state & 1)],
            self.points_pixmap[points_state],
            self.uvmap_pixmap[uvmap_state],
        ]

        rect = option.rect
        y = rect.y() + rect.height() / 2 - (self.ICON_SIZE / 2)
        x = rect.x() + self.ICON_MARGIN

        for i, pixmap in enumerate(pixmaps):
            painter.drawPixmap(x, y, pixmap)
            x += self.ICON_SIZE + self.ICON_MARGIN


class PathTextDelegate(QtWidgets.QStyledItemDelegate):

    def paint(self, painter, option, index):
        option.textElideMode = QtCore.Qt.ElideLeft
        super(PathTextDelegate, self).paint(painter, option, index)
