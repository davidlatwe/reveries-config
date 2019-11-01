
from avalon.vendor.Qt import QtWidgets, QtCore
from avalon.vendor import qtawesome


class DiffDelegate(QtWidgets.QStyledItemDelegate):

    ICON_SIZE = 16
    ICON_MARGIN = 6
    ICON_SPACE = ICON_SIZE * 3 + ICON_MARGIN * 4

    NAME_ICONS = [
        ("link", "#6A6A6A"),  # Not Match
        ("link", "#5CA6EC"),  # Match By Name
        ("link", "#ECA25C"),  # Match By Id
    ]

    POINTS_ICONS = [
        ("cube", "#EC534E"),  # Point Not Match
        ("cube", "#38DB8C"),  # Point Ok
        ("cube", "#6A6A6A"),  # Point Dimmed
    ]

    UVMAP_ICONS = [
        ("delicious", "#EC534E"),  # UV Not Match
        ("delicious", "#38DB8C"),  # UV Ok
        ("delicious", "#6A6A6A"),  # UV Dimmed
    ]

    def __init__(self, parent=None):
        super(DiffDelegate, self).__init__(parent)

        self.name_pixmap = [
            qtawesome.icon("fa.{}".format(icon),
                           color=color).pixmap(self.ICON_SIZE, self.ICON_SIZE)
            for icon, color in self.NAME_ICONS
        ]
        self.points_pixmap = [
            qtawesome.icon("fa.{}".format(icon),
                           color=color).pixmap(self.ICON_SIZE, self.ICON_SIZE)
            for icon, color in self.POINTS_ICONS
        ]
        self.uvmap_pixmap = [
            qtawesome.icon("fa.{}".format(icon),
                           color=color).pixmap(self.ICON_SIZE, self.ICON_SIZE)
            for icon, color in self.UVMAP_ICONS
        ]

    def sizeHint(self, option, index):
        size = option.rect.size()
        size.setWidth(self.ICON_SPACE)
        return size

    def paint(self, painter, option, index):
        super(DiffDelegate, self).paint(painter, option, index)

        states = index.data(QtCore.Qt.DecorationRole)
        name_state, points_state, uvmap_state = states

        name_pixmap = self.name_pixmap[name_state]
        points_pixmap = self.points_pixmap[points_state]
        uvmap_pixmap = self.uvmap_pixmap[uvmap_state]

        rect = option.rect
        center = rect.width() / 2
        half = self.ICON_SPACE / 2
        y = rect.y() + rect.height() / 2 - (self.ICON_SIZE / 2)

        x = rect.x() + center - half + self.ICON_MARGIN
        painter.drawPixmap(x, y, name_pixmap)

        x = rect.x() + center - (self.ICON_SIZE / 2)
        painter.drawPixmap(x, y, points_pixmap)

        x = rect.x() + center + half - (self.ICON_SIZE) - self.ICON_MARGIN
        painter.drawPixmap(x, y, uvmap_pixmap)
