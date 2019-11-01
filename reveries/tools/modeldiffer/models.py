
import logging
from maya import cmds

from avalon.tools import models
from avalon.vendor import qtawesome
from avalon.vendor.Qt import QtGui, QtCore
from avalon import api, io

from ....maya import utils, pipeline


main_logger = logging.getLogger("modeldiffer")


def is_supported_loader(name):
    return name in ("ModelLoader",)  # "RigLoader")


def is_supported_subset(name):
    return any(name.startswith(family)
               for family in ("model",))  # "rig"))


class OriginsModel(QtGui.QStandardItemModel):

    def __init__(self, parent=None):
        super(OriginsModel, self).__init__(parent=parent)
        self.placeholder_item = QtGui.QStandardItem(
            qtawesome.icon("fa.hand-o-right", color="white"),
            "< Select Container.. >"
        )

    def reset(self):
        self.blockSignals(True)
        self.clear()
        self.blockSignals(False)

        self.beginResetModel()

        self.appendRow(self.placeholder_item)

        host = api.registered_host()
        for container in host.ls():
            if is_supported_loader(container["loader"]):
                item = QtGui.QStandardItem(container["namespace"][1:])

                item.setData(container, QtCore.Qt.UserRole)

                self.appendRow(item)

        self.endResetModel()


class ContrastModel(QtGui.QStandardItemModel):

    def __init__(self, level, parent=None):
        super(ContrastModel, self).__init__(parent=parent)
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
                if is_supported_subset(subset["name"]):
                    yield subset

    def list_versions(self, subset_id):
        if subset_id is not None:
            filter = {"type": "version", "parent": subset_id}
            for version in io.find(filter, projection={"name": True}):
                version["name"] = "v%03d" % version["name"]
                yield version


class ComparerItem(models.Item):
    """Group by unique name and compare within same Id"""

    def __init__(self, name, id):
        self.name = name
        self.id = id

        data = {
            "matchMethod": 0,
            "originData": None,
            "contrastData": None,
            "points": 2,
            "uvmap": 2,
        }
        super(ComparerItem, self).__init__(data)

    def __eq__(self, other):
        return self.name == other

    def __repr__(self):
        return self.name

    def add_origin(self, data, matched=0):
        self.update({"originData": data})
        self["matchMethod"] = matched

    def add_contrast(self, data, matched=0):
        self.update({"contrastData": data})
        self["matchMethod"] = matched

    def has_origin(self):
        return self["originData"] is not None

    def has_contrast(self):
        return self["contrastData"] is not None

    def pop_origin(self):
        self.update({
            "matchMethod": 0,
            "originData": None,
            "points": 2,
            "uvmap": 2,
        })

    def pop_contrast(self):
        self.update({
            "matchMethod": 0,
            "contrastData": None,
            "points": 2,
            "uvmap": 2,
        })

    def compare(self):
        origin = self["originData"]
        contrast = self["contrastData"]
        self.update({
            "points": int(origin["points"] == contrast["points"]),
            "uvmap": int(origin["uvmap"] == contrast["uvmap"]),
        })


class ComparerModel(models.TreeModel):

    Columns = ["origin", "diff", "contrast"]

    HEADER_ICONS = [
        ("home", "#BEBEBE"),
        ("cloud", "#BEBEBE"),
        ("adjust", "#BEBEBE"),
    ]

    def __init__(self, parent=None):
        super(ComparerModel, self).__init__(parent=parent)

        self.header_icon = [
            qtawesome.icon("fa.{}".format(icon), color=color)
            for icon, color in self.HEADER_ICONS
        ]
        self._hasher = utils.MeshHasher()
        self._use_long_name = True
        self._origin_shared_root = ""
        self._contrast_shared_root = ""

    def hash(self, mesh):
        self._hasher.clear()
        self._hasher.set_mesh(mesh)
        self._hasher.update_points()
        self._hasher.update_uvmap()

        return self._hasher.digest()

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

    def refresh_origin(self, container=None):
        """
        Args:
            container (dict, optional): container object
        """

        if container:
            # From Avalon container node (with node name comparing)
            #
            # In this mode, we know where the hierarchy root is, so
            # we can compare with node names.
            #
            root = pipeline.get_group_from_container(container["objectName"])

            meshes = cmds.ls(cmds.sets(container["objectName"], query=True),
                             type="mesh",
                             noIntermediate=True,
                             long=True)
        else:
            # From selection (only compare with mesh hash values)
            #
            # In this mode, we can not be sure that the mesh long name is
            # comapreable, so the name will not be compared.
            #
            root = None

            meshes = cmds.listRelatives(cmds.ls(selection=True, long=True),
                                        shapes=True,
                                        noIntermediate=True,
                                        fullPath=True,
                                        type="mesh")

        if not meshes:
            main_logger.warning("No mesh selected..")
            return

        items = self._root_item.children()
        root_index = QtCore.QModelIndex()

        # Remove previous origins

        remove = list()
        for item in items:
            if item.has_contrast():
                item.pop_origin()
            else:
                remove.append(item)

        for item in remove:
            row = item.row()
            self.beginRemoveRows(root_index, row, row)
            items.remove(item)
            self.endRemoveRows()

        # Place new origins

        dataset = dict()

        for mesh in meshes:
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]

            if root and transform.startswith(root):
                namespace = container["namespace"][1:] + ":"
                name = transform[len(root):].replace(namespace, "")
            else:
                name = transform

            data = {
                "fullPath": transform,
                "points": None,
                "uvmap": None,
            }
            data.update(self.hash(mesh))

            dataset[name] = data

        shared_root = self.extract_shared_root(dataset)
        self._origin_shared_root = shared_root

        for name, data in dataset.items():

            long_name = name[len(shared_root):]
            names = long_name.split("|")
            short_name = ">" * (len(names) - 1) + "| " + names[-1]

            data["longName"] = long_name
            data["shortName"] = short_name

            if name in items:
                # Has matched contrast
                item = items[items.index(name)]
                item.add_origin(data, matched=1)
                item.compare()
            else:
                id = utils.get_id(data["fullPath"])

                for item in items:
                    if item.id == id:
                        item.add_origin(data, matched=2)
                        item.compare()
                        break

                else:
                    item = ComparerItem(name, id)
                    item.add_origin(data)
                    # Append origin
                    last = self.rowCount(root_index)
                    self.beginInsertRows(root_index, last, last)
                    self.add_child(item)
                    self.endInsertRows()

    def refresh_contrast(self, version_id):
        representation = io.find_one({"type": "representation",
                                      "name": "mayaBinary",
                                      "parent": version_id})
        if representation is None:
            main_logger.critical("Representation not found. This is a bug.")
            return

        model_profile = representation["data"].get("modelProfile")

        if model_profile is None:
            main_logger.critical("'data.modelProfile' not found."
                                 "This is a bug.")
            return

        items = self._root_item.children()
        root_index = QtCore.QModelIndex()

        # Remove previous contrasts

        remove = list()
        for item in list(items):
            if item.has_origin():
                item.pop_contrast()
            else:
                remove.append(item)

        for item in remove:
            row = item.row()
            self.beginRemoveRows(root_index, row, row)
            items.remove(item)
            self.endRemoveRows()

        # Place new contrasts

        dataset = dict()

        for id, meshes_data in model_profile.items():
            for data in meshes_data:

                name = data.pop("hierarchy")
                # No need to compare normals
                data.pop("normals")

                data["avalonId"] = id

                dataset[name] = data

        shared_root = self.extract_shared_root(dataset)
        self._contrast_shared_root = shared_root

        for name, data in dataset.items():

            long_name = name[len(shared_root):]
            names = long_name.split("|")
            short_name = ">" * (len(names) - 1) + "| " + names[-1]

            data["longName"] = long_name
            data["shortName"] = short_name

            if name in items:
                # Has matched contrast
                item = items[items.index(name)]
                item.add_contrast(data, matched=1)
                item.compare()
            else:
                id = data["avalonId"]

                for item in items:
                    if item.id == id:
                        item.add_contrast(data, matched=2)
                        item.compare()
                        break

                else:
                    item = ComparerItem(name, id)
                    item.add_contrast(data)
                    # Append contrast
                    last = self.rowCount(root_index)
                    self.beginInsertRows(root_index, last, last)
                    self.add_child(item)
                    self.endInsertRows()

    def data(self, index, role):

        if not index.isValid():
            return

        if role == QtCore.Qt.DisplayRole:
            column = index.column()

            if self.Columns[column] == "origin":
                item = index.internalPointer()
                if not item["originData"]:
                    return
                if self._use_long_name:
                    return item["originData"]["longName"]
                else:
                    return item["originData"]["shortName"]

            if self.Columns[column] == "contrast":
                item = index.internalPointer()
                if not item["contrastData"]:
                    return
                if self._use_long_name:
                    return item["contrastData"]["longName"]
                else:
                    return item["contrastData"]["shortName"]

        if role == QtCore.Qt.DecorationRole:
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
            if section == self.Columns.index("origin"):
                return self._origin_shared_root

            if section == self.Columns.index("contrast"):
                return "Published"

            if section == self.Columns.index("diff"):
                return "Diff State"

        if role == QtCore.Qt.DecorationRole:
            if section == self.Columns.index("origin"):
                return self.header_icon[0]

            if section == self.Columns.index("contrast"):
                return self.header_icon[1]

            if section == self.Columns.index("diff"):
                return self.header_icon[2]

        return super(ComparerModel, self).headerData(section,
                                                     orientation,
                                                     role)
