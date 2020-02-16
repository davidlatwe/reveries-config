
import logging

from avalon.tools import models
from avalon.vendor.Qt import Qt, QtGui, QtCore
from avalon import api, io

from . import lib

main_logger = logging.getLogger("modeldiffer")


SIDE_A = "origin"
SIDE_B = "contrast"

SIDE_A_DATA = "originData"
SIDE_B_DATA = "contrastData"

SIDE_COLOR = {
    SIDE_A: "#76D7C4",
    SIDE_B: "#E59866",
}

COLOR_DARK = "#404040"
COLOR_BRIGHT = "#A6ACAF"
COLOR_DANGER = "#E57373"


class HostContainerListModel(QtGui.QStandardItemModel):

    def __init__(self, parent=None):
        super(HostContainerListModel, self).__init__(parent=parent)
        self.placeholder_item = QtGui.QStandardItem(
            lib.icon("hand-o-right", color="white"),
            "< Select Container.. >"
        )

    def reset(self):
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)

        host = api.registered_host()
        if host is None:
            return

        self.beginResetModel()

        self.appendRow(self.placeholder_item)

        for container in host.ls():
            if lib.is_supported_loader(container["loader"]):
                item = QtGui.QStandardItem(container["namespace"][1:])

                item.setData(container, QtCore.Qt.UserRole)

                self.appendRow(item)

        self.endResetModel()


class DatabaseDocumentModel(QtGui.QStandardItemModel):

    NameFieldRole = QtCore.Qt.UserRole + 10

    def __init__(self, level, parent=None):
        super(DatabaseDocumentModel, self).__init__(parent=parent)
        self.lister = {
            "silo": self.list_silos,
            "asset": self.list_assets,
            "subset": self.list_subsets,
            "version": self.list_versions,
        }[level]

        self.placeholder = "< Select %s.. >" % level.capitalize()
        self.placeholder_item = QtGui.QStandardItem(
            lib.icon("hand-o-right", color="white"),
            self.placeholder
        )

        self.reset(None)

    def reset(self, parent):
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)

        self.beginResetModel()

        self.appendRow(self.placeholder_item)
        for document in self.lister(parent):
            item = QtGui.QStandardItem(document["name"])

            item.setData(document["_id"], QtCore.Qt.UserRole)
            item.setData(document["name"], self.NameFieldRole)

            self.appendRow(item)

        self.endResetModel()

    def list_silos(self, *args):
        for silo in io.distinct("silo"):
            yield {"name": silo, "_id": silo}

    def list_assets(self, silo):
        if silo is not None:
            filter = {"type": "asset", "silo": silo}
            for asset in io.find(filter, projection={"name": True}):
                yield asset

    def list_subsets(self, asset_id):
        if asset_id is not None:
            filter = {"type": "subset", "parent": asset_id}
            for subset in io.find(filter, projection={"name": True}):
                if lib.is_supported_subset(subset["name"]):
                    yield subset

    def list_versions(self, subset_id):
        if subset_id is not None:
            filter = {"type": "version", "parent": subset_id}
            for version in io.find(filter, projection={"name": True}):
                version["name"] = "v%03d" % version["name"]
                yield version


class ComparerItem(models.Item):
    """Group by unique name and compare within same Id"""

    sides = [
        SIDE_A,
        SIDE_B,
    ]

    def __init__(self, name, id):
        self.name = name
        self.id = id

        data = {
            SIDE_A_DATA: None,
            SIDE_B_DATA: None,
            "matchMethod": 0,
            "points": 0,
            "uvmap": 0,
        }
        super(ComparerItem, self).__init__(data)

    def __eq__(self, other):
        return self.id == other

    def get_this(self, side):
        return side + "Data"

    def get_other(self, side):
        return self.sides[not self.sides.index(side)] + "Data"

    def add_this(self, side, data, matched=0):
        this = self.get_this(side)
        self.update({this: data})
        self["matchMethod"] = matched

    def has_other(self, side):
        other = self.get_other(side)
        return self[other] is not None

    def pop_this(self, side):
        other = self.get_this(side)
        self.update({
            other: None,
            "matchMethod": 0,
            "points": 0,
            "uvmap": 0,
        })

    def compare(self):
        side_a = self[SIDE_A_DATA]
        side_b = self[SIDE_B_DATA]
        self.update({
            "points": int(side_a["points"] == side_b["points"]),
            "uvmap": int(side_a["uvmap"] == side_b["uvmap"]),
        })


class ComparerModel(models.TreeModel):

    Columns = [SIDE_A, "diff", SIDE_B]

    DiffStateRole = QtCore.Qt.UserRole + 2
    HostSelectRole = QtCore.Qt.UserRole + 3

    def __init__(self, parent=None):
        super(ComparerModel, self).__init__(parent=parent)

        self._focused_indexes = {SIDE_A: None, SIDE_B: None}
        self._focused_icons = [
            lib.icon("bullseye", color=SIDE_COLOR[SIDE_A]),
            lib.icon("bullseye", color=SIDE_COLOR[SIDE_B]),
        ]

    def refresh_side(self, side, profile, host=False):
        profile = profile or dict()

        items = self._root_item.children()
        root_index = QtCore.QModelIndex()

        # Remove previous data of this side

        to_remove = list()
        for item in items:
            if item.has_other(side):
                item.pop_this(side)
            else:
                to_remove.append(item)

        for item in to_remove:
            row = item.row()
            self.beginRemoveRows(root_index, row, row)
            items.remove(item)
            self.endRemoveRows()

        # Place new data

        not_matched_items = list(items)
        not_matched_data = list()

        def short(name):  # No namespace
            return name.rsplit("|", 1)[-1].rsplit(":", 1)[-1]

        def long(name):  # No namespace
            return "|".join(n.rsplit(":", 1)[-1] for n in name.split("|"))

        def related(this, that):
            return this == that or this.endswith(that) or that.endswith(this)

        for name, data in profile.items():
            data = {
                "fullPath": name,
                "fromHost": host,
                "shortName": short(name),
                "longName": long(name),
                "avalonId": data["avalonId"],
                "protected": data.get("protected"),
                "points": data["points"],
                "uvmap": data["uvmap"],
            }
            not_matched_data.append(data)

        not_matched_data.sort(key=lambda d: d["longName"] + d["fullPath"])

        for data in list(not_matched_data):
            # Matching avalonId & longName
            state = 0
            for item in not_matched_items:
                if item.id == data["avalonId"]:
                    state |= 1

                    if related(item.name, data["longName"]):
                        state |= 2

                if state:
                    not_matched_items.remove(item)
                    not_matched_data.remove(data)
                    item.add_this(side, data, matched=state)
                    item.compare()
                    break

        for data in list(not_matched_data):
            # Try matching only by longName
            state = 0
            for item in not_matched_items:

                if related(item.name, data["longName"]):
                    state |= 2
                    not_matched_items.remove(item)
                    not_matched_data.remove(data)
                    item.add_this(side, data, matched=state)
                    item.compare()
                    break

        for data in not_matched_data:
            # Finally, try matching by shortName
            for item in not_matched_items:
                other_side = item[item.get_other(side)]

                if other_side["shortName"] == data["shortName"]:
                    not_matched_items.remove(item)
                    item.add_this(side, data, matched=0)
                    item.compare()
                    break
            else:
                item = ComparerItem(data["longName"], data["avalonId"])
                item.add_this(side, data)
                last = self.rowCount(root_index)
                self.beginInsertRows(root_index, last, last)
                self.add_child(item)
                self.endInsertRows()

    def set_fouced(self, side, index):
        self._focused_indexes[side] = index

    def data(self, index, role):

        if not index.isValid():
            return

        if role == QtCore.Qt.DisplayRole:
            column = index.column()

            if self.Columns[column] == SIDE_A:
                item = index.internalPointer()
                if not item.get(SIDE_A_DATA):
                    return ""
                return item[SIDE_A_DATA]["shortName"]

            if self.Columns[column] == SIDE_B:
                item = index.internalPointer()
                if not item.get(SIDE_B_DATA):
                    return ""
                return item[SIDE_B_DATA]["shortName"]

        if role == QtCore.Qt.DecorationRole:
            column = index.column()

            if self.Columns[column] == SIDE_A:
                if index == self._focused_indexes[SIDE_A]:
                    return self._focused_icons[0]

            elif self.Columns[column] == SIDE_B:
                if index == self._focused_indexes[SIDE_B]:
                    return self._focused_icons[1]

        if role == QtCore.Qt.ForegroundRole:
            column = index.column()

            if self.Columns[column] == SIDE_A:
                item = index.internalPointer()
                if not item.get(SIDE_A_DATA):
                    return
                if not item[SIDE_A_DATA]["fromHost"]:
                    return QtGui.QColor("gray")

            if self.Columns[column] == SIDE_B:
                item = index.internalPointer()
                if not item.get(SIDE_B_DATA):
                    return
                if not item[SIDE_B_DATA]["fromHost"]:
                    return QtGui.QColor("gray")

        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter

        if role == QtCore.Qt.FontRole:
            column = index.column()

            if self.Columns[column] == SIDE_A:
                item = index.internalPointer()
                if not item.get(SIDE_A_DATA):
                    return
                if item[SIDE_A_DATA]["fromHost"]:
                    bold = QtGui.QFont()
                    bold.setBold(True)
                    return bold
                else:
                    return

            if self.Columns[column] == SIDE_B:
                item = index.internalPointer()
                if not item.get(SIDE_B_DATA):
                    return
                if item[SIDE_B_DATA]["fromHost"]:
                    bold = QtGui.QFont()
                    bold.setBold(True)
                    return bold
                else:
                    return

        if role == self.HostSelectRole:
            column = index.column()

            if self.Columns[column] == SIDE_A:
                item = index.internalPointer()
                if not item.get(SIDE_A_DATA):
                    return
                if item[SIDE_A_DATA]["fromHost"]:
                    return item[SIDE_A_DATA]["fullPath"]
                else:
                    return

            if self.Columns[column] == SIDE_B:
                item = index.internalPointer()
                if not item.get(SIDE_B_DATA):
                    return
                if item[SIDE_B_DATA]["fromHost"]:
                    return item[SIDE_B_DATA]["fullPath"]
                else:
                    return

        if role == self.DiffStateRole:
            column = index.column()

            if self.Columns[column] == "diff":
                item = index.internalPointer()

                name_state = item["matchMethod"]
                points_state = item["points"]
                uvmap_state = item["uvmap"]

                if not item.get(SIDE_A_DATA) or item[SIDE_A_DATA]["fromHost"]:
                    protected_A = -1
                else:
                    protected_A = item[SIDE_A_DATA]["protected"]
                if not item.get(SIDE_B_DATA) or item[SIDE_B_DATA]["fromHost"]:
                    protected_B = -1
                else:
                    protected_B = item[SIDE_B_DATA]["protected"]
                protected = (protected_A, protected_B)

                return name_state, points_state, uvmap_state, protected

        return super(ComparerModel, self).data(index, role)

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        # Make the side column editable
        if index.column() in (0, 2):  # side columns
            flags |= QtCore.Qt.ItemIsEditable

        return flags

    def headerData(self, section, orientation, role):

        if role == QtCore.Qt.DisplayRole:
            if section == self.Columns.index(SIDE_A):
                return "Name"

            if section == self.Columns.index(SIDE_B):
                return "Name"

            if section == self.Columns.index("diff"):
                return "Diff"

        if role == QtCore.Qt.ForegroundRole:
            if section == self.Columns.index(SIDE_A):
                return QtGui.QColor(SIDE_COLOR[SIDE_A])

            if section == self.Columns.index(SIDE_B):
                return QtGui.QColor(SIDE_COLOR[SIDE_B])

        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter

        if role == QtCore.Qt.FontRole:
            font = QtGui.QFont()
            font.setBold(True)
            return font

        return super(ComparerModel, self).headerData(section,
                                                     orientation,
                                                     role)


class FocusModel(models.TreeModel):

    Columns = ["side", "value"]

    def __init__(self, parent=None):
        super(FocusModel, self).__init__(parent=parent)
        self._feature = None
        self._side_icons = [
            lib.icon("bullseye", color=SIDE_COLOR[SIDE_A]),
            lib.icon("bullseye", color=SIDE_COLOR[SIDE_B]),
        ]

        node_a = models.Item({"side": SIDE_A})
        node_b = models.Item({"side": SIDE_B})

        self.nodes = {
            SIDE_A: node_a,
            SIDE_B: node_b,
        }
        self.add_child(node_a)
        self.add_child(node_b)

    def reset_sides(self):
        self.nodes[SIDE_A].clear()
        self.nodes[SIDE_A].update({"side": SIDE_A})
        self.nodes[SIDE_B].clear()
        self.nodes[SIDE_B].update({"side": SIDE_B})
        self.on_changed()

    def set_focus(self, feature):
        self._feature = feature
        self.on_changed()

    def set_side(self, side, data):
        data["side"] = side
        self.nodes[side].clear()
        self.nodes[side].update(data)
        self.on_changed()

    def on_changed(self):
        index_a = self.index(0, 1, QtCore.QModelIndex())
        index_b = self.index(1, 1, QtCore.QModelIndex())
        # passing `list()` for PyQt5 (see PYSIDE-462)
        args = () if Qt.IsPySide or Qt.IsPyQt4 else ([],)
        self.dataChanged.emit(index_a, index_b, *args)

    def data(self, index, role):

        if not index.isValid():
            return

        if role == QtCore.Qt.DisplayRole:
            if self.Columns[index.column()] == "value":
                item = index.internalPointer()
                value = item.get(self._feature, "")
                if value and self._feature == "avalonId":
                    time = lib.avalon_id_pretty_time(value)
                    value = "%s [%s]" % (time, value)
                return value
            else:
                return ""

        if role == QtCore.Qt.DecorationRole:
            if self.Columns[index.column()] == "side":
                if index.row():
                    return self._side_icons[1]
                else:
                    return self._side_icons[0]

        if role == QtCore.Qt.FontRole:

            font = QtGui.QFont("Monospace")
            font.setStyleHint(QtGui.QFont.TypeWriter)
            return font

        return super(FocusModel, self).data(index, role)

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        # Make the value column editable
        if index.column() == 1:  # value columns
            flags |= QtCore.Qt.ItemIsEditable

        return flags
