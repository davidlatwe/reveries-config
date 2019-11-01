
import logging

from avalon.vendor.Qt import QtWidgets, QtCore
from avalon import api, io
from . import models, delegates


main_logger = logging.getLogger("modeldiffer")


class OriginSelector(QtWidgets.QWidget):

    origin_picked = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super(OriginSelector, self).__init__(parent=parent)

        panel = {
            "selection": QtWidgets.QWidget(),
            "container": QtWidgets.QWidget(),
        }

        model = {
            "containerModel": models.OriginsModel(),
        }

        widget = {
            "selectionChk": QtWidgets.QCheckBox("Use Selection"),
            "selectionBtn": QtWidgets.QPushButton("Compare Selection"),
            "containerChk": QtWidgets.QCheckBox("Use Container"),
            "containerBox": QtWidgets.QComboBox(),
        }

        widget["containerBox"].setModel(model["containerModel"])

        layout = QtWidgets.QVBoxLayout(panel["selection"])
        layout.addWidget(widget["selectionChk"])
        layout.addWidget(widget["selectionBtn"])

        layout = QtWidgets.QVBoxLayout(panel["container"])
        layout.addWidget(widget["containerChk"])
        layout.addWidget(widget["containerBox"])

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(panel["selection"])
        layout.addWidget(panel["container"])

        # Connect

        widget["selectionBtn"].pressed.connect(self.on_selection_pressed)
        widget["selectionChk"].stateChanged.connect(self.on_use_selection)
        widget["containerChk"].stateChanged.connect(self.on_use_container)
        widget["containerBox"].currentIndexChanged.connect(
            self.on_container_picked)

        # Init

        self.widget = widget
        self.model = model

        widget["containerChk"].setCheckState(QtCore.Qt.Checked)

    def on_use_selection(self, state):
        inverse = QtCore.Qt.Checked if not state else QtCore.Qt.Unchecked
        self.widget["containerChk"].blockSignals(True)
        self.widget["containerChk"].setCheckState(inverse)
        self.widget["containerChk"].blockSignals(False)

        self.widget["selectionBtn"].setEnabled(state)
        self.widget["containerBox"].setEnabled(not state)

        if not state:
            self.build_container_list()

    def on_use_container(self, state):
        inverse = QtCore.Qt.Checked if not state else QtCore.Qt.Unchecked
        self.widget["selectionChk"].blockSignals(True)
        self.widget["selectionChk"].setCheckState(inverse)
        self.widget["selectionChk"].blockSignals(False)

        self.widget["selectionBtn"].setEnabled(not state)
        self.widget["containerBox"].setEnabled(state)

        if state:
            self.build_container_list()

    def on_container_picked(self):
        container = self.widget["containerBox"].currentData()
        if container is not None:
            self.origin_picked.emit(container)

    def on_selection_pressed(self):
        self.origin_picked.emit(None)

    def build_container_list(self):
        self.model["containerModel"].reset()
        self.widget["containerBox"].setCurrentIndex(0)


class ContrastSelector(QtWidgets.QWidget):

    version_changed = QtCore.Signal(io.ObjectId)

    def __init__(self, parent=None):
        super(ContrastSelector, self).__init__(parent=parent)

        panel = {
            "silo": QtWidgets.QWidget(),
            "asset": QtWidgets.QWidget(),
            "subset": QtWidgets.QWidget(),
            "version": QtWidgets.QWidget(),
        }

        label = {
            "silo": QtWidgets.QLabel("Silo"),
            "asset": QtWidgets.QLabel("Asset"),
            "subset": QtWidgets.QLabel("Subset"),
            "version": QtWidgets.QLabel("Version"),
        }

        widget = {
            "silo": QtWidgets.QComboBox(),
            "asset": QtWidgets.QComboBox(),
            "subset": QtWidgets.QComboBox(),
            "version": QtWidgets.QComboBox(),
        }

        model = {
            "silo": models.ContrastModel(level="silo"),
            "asset": models.ContrastModel(level="asset"),
            "subset": models.ContrastModel(level="subset"),
            "version": models.ContrastModel(level="version"),
        }

        view = {
            "silo": QtWidgets.QListView(),
            "asset": QtWidgets.QListView(),
            "subset": QtWidgets.QListView(),
            "version": QtWidgets.QListView(),
        }

        widget["silo"].setModel(model["silo"])
        widget["asset"].setModel(model["asset"])
        widget["subset"].setModel(model["subset"])
        widget["version"].setModel(model["version"])

        widget["silo"].setView(view["silo"])
        widget["asset"].setView(view["asset"])
        widget["subset"].setView(view["subset"])
        widget["version"].setView(view["version"])

        def build_panel(level):
            label[level].setFixedWidth(60)
            label[level].setAlignment(QtCore.Qt.AlignVCenter |
                                      QtCore.Qt.AlignRight)
            layout = QtWidgets.QHBoxLayout(panel[level])
            layout.addWidget(label[level])
            layout.addWidget(widget[level])
        build_panel("silo")
        build_panel("asset")
        build_panel("subset")
        build_panel("version")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(panel["silo"])
        layout.addSpacing(-16)
        layout.addWidget(panel["asset"])
        layout.addSpacing(-16)
        layout.addWidget(panel["subset"])
        layout.addSpacing(-16)
        layout.addWidget(panel["version"])

        # Connect

        def connect_index_changed(level, callback):
            widget[level].currentIndexChanged.connect(callback)
        connect_index_changed("silo", self.on_silo_changed)
        connect_index_changed("asset", self.on_asset_changed)
        connect_index_changed("subset", self.on_subset_changed)
        connect_index_changed("version", self.on_version_changed)

        # Init

        self._versioned = False

        self.widget = widget
        self.model = model
        self.view = view

        init_index = self.widget["silo"].findText(api.Session["AVALON_SILO"])
        self.widget["silo"].setCurrentIndex(init_index)

    def _on_level_changed(self, level, child_level):
        combobox = self.widget[level]
        child_model = self.model[child_level]
        child_box = self.widget[child_level]

        data = combobox.currentData()
        child_model.reset(data)
        child_box.setCurrentIndex(0)

    def on_silo_changed(self):
        self._on_level_changed("silo", "asset")

    def on_asset_changed(self):
        self._on_level_changed("asset", "subset")

    def on_subset_changed(self):
        self._on_level_changed("subset", "version")

    def on_version_changed(self):
        combobox = self.widget["version"]
        data = combobox.currentData()
        if data:
            self.version_changed.emit(data)

    def on_origin_picked(self, container):
        if container is None:
            return

        asset = io.find_one({"_id": io.ObjectId(container["assetId"])})
        if asset is None:
            main_logger.error("Asset not found.")
            return

        self.widget["silo"].setCurrentText(asset["silo"])
        self.widget["asset"].setCurrentText(asset["name"])

        subset = io.find_one({"_id": io.ObjectId(container["subsetId"])})
        if subset is None:
            main_logger.error("Subset not found.")
            return

        self.widget["subset"].setCurrentText(subset["name"])


class ComparerTable(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(ComparerTable, self).__init__(parent=parent)

        data = {
            "model": models.ComparerModel(),
            "proxy": QtCore.QSortFilterProxyModel(),
            "view": QtWidgets.QTreeView(),
            "diff": delegates.DiffDelegate(),
        }

        data["view"].setIndentation(20)
        data["view"].setStyleSheet("""
            QTreeView::item{
                padding: 6px 1px;
                border: 0px;
            }
        """)
        data["view"].setAllColumnsShowFocus(True)
        data["view"].setAlternatingRowColors(True)
        data["view"].setSortingEnabled(True)
        data["view"].setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)

        header = data["view"].header()
        header.setMinimumSectionSize(delegates.DiffDelegate.ICON_SPACE)

        # Delegate
        diff_delegate = data["diff"]
        column = data["model"].Columns.index("diff")
        data["view"].setItemDelegateForColumn(column, diff_delegate)

        data["proxy"].setSourceModel(data["model"])
        data["view"].setModel(data["proxy"])

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(data["view"])

        # Init

        self.data = data

    def on_version_changed(self, version_id):
        self.data["model"].refresh_contrast(version_id)

    def on_origin_picked(self, container=None):
        self.data["model"].refresh_origin(container)
