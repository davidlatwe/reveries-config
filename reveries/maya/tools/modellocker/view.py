
from maya.api import OpenMaya  # API 2.0
from maya import cmds
from avalon.vendor.Qt import Qt, QtWidgets, QtCore
from avalon.vendor import qtawesome
from avalon.tools import lib as tools_lib

from . import model
from ... import callbacks
from ....lib import pindict


class SelectionOutline(QtWidgets.QWidget):

    CALLBACK_TOKEN = "modellocker.SelectionOutline"

    def __init__(self, parent=None):
        super(SelectionOutline, self).__init__(parent=parent)

        data = pindict({
            "model": model.SelectionModel(),
            "proxy": QtCore.QSortFilterProxyModel(),
        })

        panels = {
            "header": QtWidgets.QWidget(),
            "body": QtWidgets.QWidget(),
            "footer": QtWidgets.QWidget(),
        }

        widgets = pindict({
            "view": QtWidgets.QTreeView(),
            "lock": QtWidgets.QPushButton("Lock"),
            "unlock": QtWidgets.QPushButton("Unlock"),
            "save": QtWidgets.QPushButton("Save"),
            "refresh": QtWidgets.QPushButton(),
        })

        data["proxy"].setSourceModel(data["model"])
        widgets["view"].setModel(data["proxy"])

        with widgets.pin("view") as _:
            _.setAllColumnsShowFocus(True)
            _.setAlternatingRowColors(True)
            _.setSortingEnabled(True)
            _.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            _.sortByColumn(1, QtCore.Qt.AscendingOrder)
            _.setSelectionMode(_.ExtendedSelection)

            _.setIndentation(20)
            _.setStyleSheet("""
                QTreeView::item{
                    padding: 4px 1px;
                    border: 0px;
                }
            """)

            _.setColumnWidth(0, 240)

        layout = QtWidgets.QHBoxLayout(panels["header"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setMargin(0)
        layout.addStretch()
        layout.addWidget(widgets["refresh"])

        layout = QtWidgets.QHBoxLayout(panels["body"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setMargin(0)
        layout.addWidget(widgets["view"])

        layout = QtWidgets.QHBoxLayout(panels["footer"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setMargin(0)
        layout.addWidget(widgets["lock"])
        layout.addWidget(widgets["unlock"])
        layout.addWidget(widgets["save"])

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setMargin(0)
        layout.addWidget(panels["header"])
        layout.addWidget(panels["body"])
        layout.addWidget(panels["footer"])

        widgets["view"].customContextMenuRequested.connect(self.on_menu)
        widgets["lock"].clicked.connect(lambda: self.on_locked(True))
        widgets["unlock"].clicked.connect(lambda: self.on_locked(False))
        widgets["save"].clicked.connect(self.on_saved)
        widgets["refresh"].clicked.connect(self.on_refreshed)

        icon = qtawesome.icon("fa.lock", color="gray")
        widgets["lock"].setIcon(icon)
        icon = qtawesome.icon("fa.unlock", color="gray")
        widgets["unlock"].setIcon(icon)
        icon = qtawesome.icon("fa.save", color="gray")
        widgets["save"].setIcon(icon)
        icon = qtawesome.icon("fa.refresh", color="white")
        widgets["refresh"].setIcon(icon)

        self.data = data
        self.widgets = widgets

        self._selection_sync = True

    def on_menu(self, point):
        point_index = self.widgets["view"].indexAt(point)
        if not point_index.isValid():
            return

        menu = QtWidgets.QMenu(self)

        select_action = QtWidgets.QAction("Select..", menu)
        select_action.triggered.connect(self.act_select)

        menu.addAction(select_action)

        # Show the context action menu
        global_point = self.widgets["view"].mapToGlobal(point)
        # Tweak menu position so user can directly hit select action without
        # moving cursor much.
        global_point.setX(global_point.x() - 70)
        global_point.setY(global_point.y() + 10)
        action = menu.exec_(global_point)
        if not action:
            return

    def act_select(self):
        selection_model = self.widgets["view"].selectionModel()
        selection = selection_model.selection()
        source_selection = self.data["proxy"].mapSelectionToSource(selection)

        nodes = list()

        for index in source_selection.indexes():
            if not index.isValid():
                continue
            node = index.internalPointer()
            nodes.append(node["node"])

        self._selection_sync = False
        cmds.select(nodes, noExpand=True)
        self._selection_sync = True

    def start(self):
        self.stop()
        callbacks.register_event_callback(self.CALLBACK_TOKEN,
                                          "SelectionChanged",
                                          self.on_selected)

    def stop(self):
        callbacks.deregister_event_callback(self.CALLBACK_TOKEN)

    def on_selected(self, *args, **kwargs):
        # Sync view selection

        if not self._selection_sync:
            return

        OBJ = {
            "view": self.widgets["view"],
            "model": self.widgets["view"].model(),
        }

        if not OBJ["model"].rowCount(QtCore.QModelIndex()):
            return

        OBJ["view"].clearSelection()

        selected = set()

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
                selected.add(fullname)
            finally:
                iter.next()

        if not selected:
            return

        # Hightlight item
        selection_model = OBJ["view"].selectionModel()
        selection = selection_model.selection()

        for index in tools_lib.iter_model_rows(OBJ["model"], 0):
            item = index.data(model.SelectionModel.ItemRole)
            node = item.get("node")
            if node in selected:
                selection.select(index, index.sibling(index.row(), 1))
                selected.remove(node)

            if len(selected) == 0:
                break

        selection_model.select(selection, selection_model.Select)
        OBJ["view"].scrollTo(index)  # Ensure visible

    def on_refreshed(self):
        self.data["model"].refresh()
        self.widgets["view"].expandAll()
        self.on_selected()

    def on_locked(self, lock):
        # If is latest !!!!
        selection_model = self.widgets["view"].selectionModel()
        selection = selection_model.selection()
        source_selection = self.data["proxy"].mapSelectionToSource(selection)

        for index in source_selection.indexes():
            if not index.isValid():
                continue
            node = index.internalPointer()

            if not node["isLatest"]:
                continue

            node["setLocked"] = lock

            # passing `list()` for PyQt5 (see PYSIDE-462)
            args = () if Qt.IsPySide or Qt.IsPyQt4 else ([],)
            self.data["model"].dataChanged.emit(index, index, *args)

    def on_saved(self):
        self.data["model"].write_database()
