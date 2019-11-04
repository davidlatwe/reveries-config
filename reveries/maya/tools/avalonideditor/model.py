
from maya.api import OpenMaya  # API 2.0
from maya import cmds

from avalon.tools import models
from avalon.vendor import qtawesome
from avalon.vendor.Qt import QtCore, QtGui
from avalon import io
from ... import callbacks, utils


_identifier = utils.Identifier()
_cached_asset = dict()


def asset_by_id(id):
    if id not in _cached_asset:
        asset = io.find_one({"_id": io.ObjectId(id)},
                            projection={"name": True})
        if not asset:
            return None

        _cached_asset[id] = asset["name"]

    return _cached_asset[id]


class SelectionModel(models.TreeModel):

    Columns = ["asset", "namespace", "name", "Id", "time"]

    NodeNameDataRole = QtCore.Qt.UserRole + 10

    CALLBACK_TOKEN = "avalonideditor.model.SelectionModel"

    REFERENCE_ICONS = [
        ("circle-thin", "#516464"),
        ("circle", "#3164C8"),
    ]
    STATUS_ICONS = [
        ("check-circle", "#38DB8C"),  # Clean, Ok
        ("copy", "#ECA519"),  # Duplicated
        ("question-circle", "#EC534E"),  # Untracked
        ("check-circle", "#ECA519"),  # Duplicate source
        ("copy", "#516464"),  # Duplicated but referenced
        ("meh-o", "#516464"),  # Untracked but referenced
    ]

    def __init__(self, parent=None):
        super(SelectionModel, self).__init__(parent=parent)

        self.status_icon = [
            qtawesome.icon("fa.{}".format(icon), color=color)
            for icon, color in self.STATUS_ICONS
        ]
        self.reference_icon = [
            qtawesome.icon("fa.{}".format(icon), color=color)
            for icon, color in self.REFERENCE_ICONS
        ]

        self._duplicated_id = set()
        self._selecting_back = False
        self._selection_freezed = False

    def listen(self):
        callbacks.register_event_callback(self.CALLBACK_TOKEN,
                                          "SelectionChanged",
                                          self.on_selected)

    def stop(self):
        callbacks.deregister_event_callback(self.CALLBACK_TOKEN)

    def on_selected(self, *args, **kwargs):

        if self._selecting_back or self._selection_freezed:
            return

        selection = list()

        sel = OpenMaya.MGlobal.getActiveSelectionList()
        iter = OpenMaya.MItSelectionList(sel)

        # Loop though iterator objects
        while not iter.isDone():
            try:
                obj = iter.getDependNode()
                dagPath = OpenMaya.MDagPath.getAPathTo(obj)
                fullname = dagPath.fullPathName()
            except RuntimeError:
                pass
            else:
                selection.append(fullname)
            finally:
                iter.next()

        if not selection:
            return

        self.clear()
        self.beginResetModel()

        duplicated_id = set()

        for node in selection:

            asset = asset_by_id(_identifier.read_namespace(node))
            name = node.rsplit("|", 1)[-1]
            node_id = _identifier.read_address(node)
            node_id_status = _identifier.status(node)
            time = _identifier.get_time(node)

            if node_id_status == utils.Identifier.Duplicated:
                duplicated_id.add(node_id)

            namespaced = ":" in name
            namespace, name = name.rsplit(":", 1) if namespaced else ("", name)

            is_referenced = cmds.referenceQuery(node, isNodeReferenced=True)

            node_item = models.Item()
            node_item.update({
                "asset": asset,
                "name": name,
                "Id": node_id,
                "status": node_id_status,
                "time": time,
                "node": node,
                "namespace": namespace,
                "isReferenced": is_referenced,
            })

            self.add_child(node_item)

        self._duplicated_id = duplicated_id

        self.endResetModel()

    def data(self, index, role):

        if not index.isValid():
            return

        if role == QtCore.Qt.FontRole:

            if index.column() in (self.Columns.index("Id"),
                                  self.Columns.index("name"),):
                font = QtGui.QFont("Monospace")
                font.setStyleHint(QtGui.QFont.TypeWriter)
                font.setBold(True)
                return font

        if role == QtCore.Qt.DecorationRole:

            if index.column() == self.Columns.index("Id"):
                node = index.internalPointer()
                status = node["status"]

                if (status == utils.Identifier.Clean and
                        node["Id"] in self._duplicated_id):
                    # Is duplicate source
                    status = 3

                elif node["isReferenced"]:

                    if status == utils.Identifier.Untracked:
                        # Is referenced but untracked
                        status = 5

                    elif status == utils.Identifier.Duplicated:
                        # Is referenced but duplicated
                        status = 4

                return self.status_icon[status]

            if index.column() == self.Columns.index("name"):
                node = index.internalPointer()
                is_referenced = node["isReferenced"]

                return self.reference_icon[is_referenced]

        if role == self.NodeNameDataRole:

            node = index.internalPointer()
            return (node["name"],
                    node["namespace"],
                    node["isReferenced"])

        return super(SelectionModel, self).data(index, role)

    def select_back(self, indexes):
        nodes = list()

        for index in indexes:
            if not index.isValid():
                continue
            node = index.internalPointer()
            nodes.append(node["node"])

        self._selecting_back = True
        cmds.select(nodes, noExpand=True)
        self._selecting_back = False


class SelectionModelProxy(QtCore.QSortFilterProxyModel):
    pass
