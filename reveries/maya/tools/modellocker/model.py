
from maya import cmds

from avalon.tools import models
from avalon.vendor import qtawesome
from avalon.vendor.Qt import QtCore, QtGui
from avalon import io, api
from ... import utils


class SelectionModel(models.TreeModel):

    Columns = ["namespace", "name"]

    STATUS_ICONS = [
        ("unlock", "#404040"),
        ("lock", "#A6ACAF"),
        ("unlock", "#17A589"),  # modified
        ("lock", "#B9770E"),  # modified
    ]

    def __init__(self, parent=None):
        super(SelectionModel, self).__init__(parent=parent)

        self.status_icon = [
            qtawesome.icon("fa.{}".format(icon), color=color)
            for icon, color in self.STATUS_ICONS
        ]

    def refresh(self):
        model_containers = list()

        host = api.registered_host()
        for container in host.ls():
            if container["loader"] == "ModelLoader":
                model_containers.append(container)

        self.clear()
        self.beginResetModel()

        for container in model_containers:

            subset_id = io.ObjectId(container["subsetId"])
            version_id = io.ObjectId(container["versionId"])
            version = io.find_one({"_id": version_id})
            latest = io.find_one({"type": "version", "parent": subset_id},
                                 sort=[("name", -1)],
                                 projection={"name": True})
            latest_repr = io.find_one({"type": "representation",
                                       "parent": latest["_id"],
                                       "name": "mayaBinary"})

            # Is latest version loaded ?
            is_latest = latest["name"] == version["name"]

            versions = io.find({"type": "version", "parent": subset_id},
                               sort=[("name", -1)])
            for version in versions:
                repr = io.find_one({"type": "representation",
                                    "parent": version["_id"],
                                    "name": "mayaBinary"})

                protected = repr["data"].get("modelProtected")
                if protected is not None:
                    # Get protected list from previous version if not found
                    break
            protected = protected or set()

            namespace = container["namespace"]
            subset_group = container["subsetGroup"]
            subset_item = models.Item()
            subset_item.update({
                "subsetId": subset_id,
                "representation": latest_repr,
                "namespace": namespace,
                "node": subset_group,
                "name": subset_group.rsplit("|", 1)[-1][len(namespace):],
                "isLatest": is_latest,
            })

            members = cmds.sets(container["objectName"], query=True)
            for node in cmds.ls(members,
                                type="transform",
                                referencedNodes=True,
                                long=True):
                meshes = cmds.listRelatives(node,
                                            shapes=True,
                                            noIntermediate=True,
                                            type="mesh")
                if not meshes:
                    continue

                id = utils.get_id(node)
                is_locked = id in protected

                node_item = models.Item()
                node_item.update({
                    "node": node,
                    "name": node.rsplit("|", 1)[-1][len(namespace):],
                    "avalonId": id,
                    "isLocked": is_locked,
                    "isLatest": is_latest,
                    "setLocked": None,
                })

                subset_item.add_child(node_item)

            self.add_child(subset_item)

        self.endResetModel()

    def data(self, index, role):

        if not index.isValid():
            return

        if role == QtCore.Qt.FontRole:

            if index.column() in (self.Columns.index("namespace"),
                                  self.Columns.index("name"),):
                node = index.internalPointer()
                font = QtGui.QFont("Monospace")
                font.setStyleHint(QtGui.QFont.TypeWriter)
                font.setBold(node["isLatest"])
                font.setItalic(not node["isLatest"])
                return font

        if role == QtCore.Qt.ForegroundRole:

            if index.column() in (self.Columns.index("namespace"),
                                  self.Columns.index("name"),):
                node = index.internalPointer()
                if not node["isLatest"]:
                    return QtGui.QColor(120, 120, 120)

        if role == QtCore.Qt.DecorationRole:

            if index.column() == self.Columns.index("name"):
                node = index.internalPointer()
                if "isLocked" in node:
                    is_locked = node["isLocked"]
                    set_locked = node["setLocked"]
                    if set_locked is None or set_locked == is_locked:
                        return self.status_icon[is_locked]
                    else:
                        return self.status_icon[set_locked + 2]

        return super(SelectionModel, self).data(index, role)

    def write_database(self):
        # Check database if still being latest
        for item in self._root_item.children():
            subset_id = item["subsetId"]
            latest_repr = item["representation"]
            latest = io.find_one({"type": "version", "parent": subset_id},
                                 sort=[("name", -1)],
                                 projection={"name": True})
            if not latest_repr["parent"] == latest["_id"]:
                # Found new version, should do refresh
                return

        for item in self._root_item.children():
            if not item["isLatest"]:
                continue

            latest_repr = item["representation"]
            protected = set()

            for node in item.children():
                is_locked = node["isLocked"]
                set_locked = node["setLocked"]

                if set_locked is None:
                    if is_locked:
                        protected.add(node["avalonId"])
                elif set_locked:
                    # Set to Lock
                    protected.add(node["avalonId"])

            io.update_many({"_id": latest_repr["_id"]},
                           {"$set": {"data.modelProtected": list(protected)}})
