
import logging

from avalon.tools import models
from avalon.vendor import qtawesome
from avalon.vendor.Qt import QtGui, QtCore
from avalon import api, io

from . import lib


SIDE_A = "origin"
SIDE_B = "contrast"

SIDE_A_DATA = "originData"
SIDE_B_DATA = "contrastData"

SIDE_COLOR = {
    SIDE_A: "#ECD781",
    SIDE_B: "#E79A73",
}


main_logger = logging.getLogger("modeldiffer")


class HostContainerListModel(QtGui.QStandardItemModel):

    def __init__(self, parent=None):
        super(HostContainerListModel, self).__init__(parent=parent)
        self.placeholder_item = QtGui.QStandardItem(
            qtawesome.icon("fa.hand-o-right", color="white"),
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
            qtawesome.icon("fa.hand-o-right", color="white"),
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
            "points": 2,
            "uvmap": 2,
        }
        super(ComparerItem, self).__init__(data)

    def __eq__(self, other):
        return self.name == other

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
            "points": 2,
            "uvmap": 2,
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

    HEADER_ICONS = [
        ("cubes", SIDE_COLOR[SIDE_A]),
        ("cubes", SIDE_COLOR[SIDE_B]),
        ("adjust", "#BEBEBE"),
    ]

    def __init__(self, parent=None):
        super(ComparerModel, self).__init__(parent=parent)

        self.header_icon = [
            qtawesome.icon("fa.{}".format(icon), color=color)
            for icon, color in self.HEADER_ICONS
        ]

        self._use_long_name = False
        self._origin_shared_root = ""
        self._contrast_shared_root = ""

    def extract_shared_root(self, nodes):
        shared_root = ""
        for path in next(iter(nodes))[1:].split("|"):
            path = "|" + path

            for name in nodes:
                if not name.startswith(shared_root + path + "|"):
                    return shared_root
            else:
                shared_root += path

        return shared_root

    def set_use_long_name(self, value):
        self._use_long_name = value

    def refresh_side(self, side, profile, host=False):

        items = self._root_item.children()
        root_index = QtCore.QModelIndex()

        # Remove previous data of this side

        remove = list()
        for item in items:
            if item.has_other(side):
                item.pop_this(side)
            else:
                remove.append(item)

        for item in remove:
            row = item.row()
            self.beginRemoveRows(root_index, row, row)
            items.remove(item)
            self.endRemoveRows()

        # Place new data

        shared_root = self.extract_shared_root(profile)
        self._origin_shared_root = shared_root

        for name, data in profile.items():

            data["longName"] = data.get("fullPath", name)
            data["shortName"] = name[len(shared_root):]
            data["fromHost"] = host

            if name in items:
                # Has matched
                item = items[items.index(name)]
                item.add_this(side, data, matched=1)
                item.compare()
            else:
                id = data["avalonId"]

                for item in items:
                    if item.id == id:
                        # Matched by Id
                        item.add_this(side, data, matched=2)
                        item.compare()
                        break

                else:
                    # No match
                    item = ComparerItem(name, id)
                    item.add_this(side, data)
                    last = self.rowCount(root_index)
                    self.beginInsertRows(root_index, last, last)
                    self.add_child(item)
                    self.endInsertRows()

    def data(self, index, role):

        if not index.isValid():
            return

        if role == QtCore.Qt.DisplayRole:
            column = index.column()

            if self.Columns[column] == SIDE_A:
                item = index.internalPointer()
                if not item.get(SIDE_A_DATA):
                    return
                if self._use_long_name:
                    return item[SIDE_A_DATA]["longName"]
                else:
                    return item[SIDE_A_DATA]["shortName"]

            if self.Columns[column] == SIDE_B:
                item = index.internalPointer()
                if not item.get(SIDE_B_DATA):
                    return
                if self._use_long_name:
                    return item[SIDE_B_DATA]["longName"]
                else:
                    return item[SIDE_B_DATA]["shortName"]

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
                    return item[SIDE_A_DATA]["longName"]
                else:
                    return

            if self.Columns[column] == SIDE_B:
                item = index.internalPointer()
                if not item.get(SIDE_B_DATA):
                    return
                if item[SIDE_B_DATA]["fromHost"]:
                    return item[SIDE_B_DATA]["longName"]
                else:
                    return

        if role == self.DiffStateRole:
            column = index.column()

            if self.Columns[column] == "diff":
                item = index.internalPointer()

                name_state = item["matchMethod"]
                points_state = item["points"]
                uvmap_state = item["uvmap"]

                return name_state, points_state, uvmap_state

        return super(ComparerModel, self).data(index, role)

    def headerData(self, section, orientation, role):

        if role == QtCore.Qt.DisplayRole:
            if section == self.Columns.index(SIDE_A):
                return "A"

            if section == self.Columns.index(SIDE_B):
                return "B"

            if section == self.Columns.index("diff"):
                return "Diff"

        if role == QtCore.Qt.DecorationRole:
            if section == self.Columns.index(SIDE_A):
                return self.header_icon[0]

            if section == self.Columns.index(SIDE_B):
                return self.header_icon[1]

            if section == self.Columns.index("diff"):
                return self.header_icon[2]

        return super(ComparerModel, self).headerData(section,
                                                     orientation,
                                                     role)
