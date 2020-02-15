
from avalon.vendor.Qt import QtWidgets, QtCore
from . import models, lib


FEATURE_ICONS = {
    "id": "hashtag",
    "name": "align-left",
    "mesh": "cube",
    "uv": "delicious",
}


class DiffDelegate(QtWidgets.QStyledItemDelegate):

    ICON_SIZE = 16
    ICON_MARGIN = 6
    ICON_COUNT = 6
    ICON_SPACE = ICON_SIZE * ICON_COUNT + ICON_MARGIN * (ICON_COUNT + 1)

    ID_ICONS = [
        (FEATURE_ICONS["id"], models.COLOR_DARK),  # Not Match
        (FEATURE_ICONS["id"], models.COLOR_BRIGHT),  # Match By Id, & 2
    ]

    NAME_ICONS = [
        (FEATURE_ICONS["name"], models.COLOR_DARK),  # Not Match
        (FEATURE_ICONS["name"], models.COLOR_BRIGHT),  # Match By Name, & 1
    ]

    POINTS_ICONS = [
        (FEATURE_ICONS["mesh"], models.COLOR_DANGER),  # Point Not Match
        (FEATURE_ICONS["mesh"], models.COLOR_BRIGHT),  # Point Ok
        (FEATURE_ICONS["mesh"], models.COLOR_DARK),  # Point Dimmed
    ]

    UVMAP_ICONS = [
        (FEATURE_ICONS["uv"], models.COLOR_DANGER),  # UV Not Match
        (FEATURE_ICONS["uv"], models.COLOR_BRIGHT),  # UV Ok
        (FEATURE_ICONS["uv"], models.COLOR_DARK),  # UV Dimmed
    ]

    LOCK_ICONS = [
        ("ellipsis-h", models.COLOR_DARK),  # Not published
        ("unlock", models.COLOR_DARK),  # Not Protected
        ("lock", "#B9770E"),  # Protected
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
        self.lock_icon = [
            lib.icon(n, c).pixmap(*s) for n, c in self.LOCK_ICONS
        ]

    def sizeHint(self, option, index):
        size = option.rect.size()
        size.setWidth(self.ICON_SPACE)
        return size

    def paint(self, painter, option, index):
        # super(DiffDelegate, self).paint(painter, option, index)

        states = index.data(self.DiffStateRole)
        name_state, points_state, uvmap_state, protected = states
        protected_A, protected_B = protected

        pixmaps = [
            self.lock_icon[protected_A + 1],
            self.id_pixmap[bool(name_state & 2)],
            self.name_pixmap[bool(name_state & 1)],
            self.points_pixmap[points_state],
            self.uvmap_pixmap[uvmap_state],
            self.lock_icon[protected_B + 1],
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

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        editor.setReadOnly(True)
        return editor

    def setEditorData(self, editor, index):
        value = index.data(QtCore.Qt.DisplayRole)
        editor.setText(value)
