
import logging

from avalon.vendor.Qt import QtWidgets, QtCore
from avalon import api, io
from . import models, delegates, lib
from ...lib import pindict


main_logger = logging.getLogger("modeldiffer")


SIDE_A = models.SIDE_A
SIDE_B = models.SIDE_B

SIDE_COLOR = models.SIDE_COLOR


def has_host():
    return lib.profile_from_host is not NotImplemented


class SelectorWidget(QtWidgets.QWidget):

    container_picked = QtCore.Signal(str, dict)
    host_selected = QtCore.Signal(str)
    version_changed = QtCore.Signal(str, io.ObjectId)

    def __init__(self, side, parent=None):
        super(SelectorWidget, self).__init__(parent=parent)

        def icon(name):
            return lib.icon(name, color=SIDE_COLOR[side])

        body = {
            "tab": QtWidgets.QTabWidget(),
        }

        selector = {
            "host": HostSelectorWidget(),
            "databse": DatabaseSelectorWidget(),
        }

        body["tab"].addTab(selector["databse"], icon("cloud"), "Published")
        body["tab"].addTab(selector["host"], icon("home"), "In Scene")

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(body["tab"])

        # Connect

        body["tab"].currentChanged.connect(self.on_tab_changed)
        selector["host"].container_picked.connect(self.on_container_picked)
        selector["host"].host_selected.connect(self.on_host_selected)
        selector["databse"].version_changed.connect(self.on_version_changed)

        # Init

        self.selector = selector
        self.side = side
        self._host_tab_enabled = False

        if not has_host() or side == SIDE_B:
            body["tab"].setCurrentIndex(0)
        else:
            body["tab"].setCurrentIndex(1)

    def connect_comparer(self, comparer):
        self.container_picked.connect(comparer.on_container_picked)
        self.host_selected.connect(comparer.on_host_selected)
        self.version_changed.connect(comparer.on_version_changed)

    def on_tab_changed(self, index):
        self._host_tab_enabled = index

    def on_container_picked(self, container):
        if self._host_tab_enabled:
            self.container_picked.emit(self.side, container)

    def on_host_selected(self):
        if self._host_tab_enabled:
            self.host_selected.emit(self.side)

    def on_version_changed(self, version_id):
        if not self._host_tab_enabled:
            self.version_changed.emit(self.side, version_id)


class HostSelectorWidget(QtWidgets.QWidget):

    container_picked = QtCore.Signal(dict)
    host_selected = QtCore.Signal()

    def __init__(self, parent=None):
        super(HostSelectorWidget, self).__init__(parent=parent)

        panel = {
            "selection": QtWidgets.QWidget(),
            "container": QtWidgets.QWidget(),
        }

        model = {
            "containerModel": models.HostContainerListModel(),
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

        widget["selectionChk"].stateChanged.connect(self.on_use_selection)
        widget["containerChk"].stateChanged.connect(self.on_use_container)
        widget["selectionBtn"].pressed.connect(self.on_selection_pressed)
        widget["containerBox"].currentIndexChanged.connect(
            self.on_container_picked)

        # Init

        self.widget = widget
        self.model = model

        widget["containerChk"].setCheckState(QtCore.Qt.Checked)

        # Confirm host registered
        if not has_host():
            # Disable all widgets
            for widget in self.widget.values():
                widget.setEnabled(False)

    def build_container_list(self):
        self.model["containerModel"].reset()
        self.widget["containerBox"].setCurrentIndex(0)

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
        self.container_picked.emit(container)

    def on_selection_pressed(self):
        self.host_selected.emit()


class DatabaseSelectorWidget(QtWidgets.QWidget):

    version_changed = QtCore.Signal(io.ObjectId)

    def __init__(self, parent=None):
        super(DatabaseSelectorWidget, self).__init__(parent=parent)

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
            "silo": models.DatabaseDocumentModel(level="silo"),
            "asset": models.DatabaseDocumentModel(level="asset"),
            "subset": models.DatabaseDocumentModel(level="subset"),
            "version": models.DatabaseDocumentModel(level="version"),
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

        self.widget = widget
        self.model = model
        self.view = view
        self._first_run = True

        silo = api.Session.get("AVALON_SILO")
        if silo:
            init_index = self.widget["silo"].findText(silo)
            self.widget["silo"].setCurrentIndex(init_index)

        asset = api.Session.get("AVALON_ASSET")
        if silo and asset:
            init_index = self.widget["asset"].findText(asset)
            self.widget["asset"].setCurrentIndex(init_index)

    def _on_level_changed(self, level, child_level):
        combobox = self.widget[level]
        child_model = self.model[child_level]
        child_box = self.widget[child_level]

        name_role = models.DatabaseDocumentModel.NameFieldRole
        doc_name = child_box.currentData(role=name_role)
        data = combobox.currentData()

        child_model.reset(data)
        child_count = child_box.count()

        if not child_count > 1:
            child_box.setCurrentIndex(0)

        elif child_level == "asset":
            child_box.setCurrentIndex(0)

        elif child_level == "subset":
            if doc_name:
                index = child_box.findData(doc_name, role=name_role)
                index = 1 if index == -1 else index
            else:
                index = 1
            child_box.setCurrentIndex(index)

        elif child_level == "version":
            index = child_count - 1
            child_box.setCurrentIndex(index)
            if self._first_run:
                # Wait for GUI to be ready
                self._first_run = False
                data = child_box.currentData()
                lib.defer(500, lambda: self.version_changed.emit(data))

    def on_silo_changed(self):
        self._on_level_changed("silo", "asset")

    def on_asset_changed(self):
        self._on_level_changed("asset", "subset")

    def on_subset_changed(self):
        self._on_level_changed("subset", "version")

    def on_version_changed(self):
        combobox = self.widget["version"]
        data = combobox.currentData()
        self.version_changed.emit(data)

    def on_container_picked(self, container):
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


class ComparingTable(QtWidgets.QWidget):

    picked = QtCore.Signal(str, dict)
    focus_enabled = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(ComparingTable, self).__init__(parent=parent)

        data = {
            "model": models.ComparerModel(),
            "proxy": QtCore.QSortFilterProxyModel(),
            "view": QtWidgets.QTreeView(),
            "diff": delegates.DiffDelegate(),
            "path": delegates.PathTextDelegate(),
        }

        data["view"].setIndentation(2)
        data["view"].setStyleSheet("""
            QTreeView::item{
                padding: 4px 1px;
                border: 0px;
            }
        """)
        data["view"].setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        data["view"].setAllColumnsShowFocus(True)
        data["view"].setAlternatingRowColors(False)
        data["view"].setSortingEnabled(True)
        data["view"].setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectItems)
        data["view"].setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)

        # Delegate
        diff_delegate = data["diff"]
        column = data["model"].Columns.index("diff")
        data["view"].setItemDelegateForColumn(column, diff_delegate)

        path_delegate = data["path"]
        column = data["model"].Columns.index(SIDE_A)
        data["view"].setItemDelegateForColumn(column, path_delegate)
        column = data["model"].Columns.index(SIDE_B)
        data["view"].setItemDelegateForColumn(column, path_delegate)

        # Set Model
        data["proxy"].setSourceModel(data["model"])
        data["view"].setModel(data["proxy"])

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(data["view"])

        # Init
        header = data["view"].header()
        header.setMinimumSectionSize(data["diff"].ICON_SPACE)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionsMovable(False)

        data["view"].setColumnWidth(1, data["diff"].ICON_SPACE)

        self.data = data
        self._focusing = False

        # Connect
        data["view"].customContextMenuRequested.connect(self.on_context_menu)
        data["view"].clicked.connect(self.on_focused)
        self.focus_enabled.connect(self.on_focus_enabled)

    def on_context_menu(self, point):
        point_index = self.data["view"].indexAt(point)
        if not point_index.isValid():
            return

        menu = QtWidgets.QMenu(self)

        if lib.select_from_host is not NotImplemented:
            select_action = QtWidgets.QAction("Select", menu)
            select_action.triggered.connect(self.act_select_nodes)

            menu.addAction(select_action)

        # Show the context action menu
        global_point = self.data["view"].mapToGlobal(point)
        action = menu.exec_(global_point)
        if not action:
            return

    def on_version_changed(self, side, version_id):
        if version_id is not None:
            profile = lib.profile_from_database(version_id)
        else:
            profile = None
        self.data["model"].refresh_side(side, profile)
        self.update()

    def on_container_picked(self, side, container):
        if container is not None:
            profile = lib.profile_from_host(container)
        else:
            profile = None
        self.data["model"].refresh_side(side, profile, host=True)
        self.update()

    def on_host_selected(self, side):
        profile = lib.profile_from_host()
        self.data["model"].refresh_side(side, profile, host=True)
        self.update()

    def act_select_nodes(self):
        selection_model = self.data["view"].selectionModel()
        selection = selection_model.selection()
        source_selection = self.data["proxy"].mapSelectionToSource(selection)

        model = self.data["model"]
        names = list()
        for index in source_selection.indexes():
            name = index.data(model.HostSelectRole)
            if name is not None:
                names.append(name)

        lib.select_from_host(names)

    def on_focus_enabled(self, enable):
        if not enable:
            self.data["model"].set_fouced(SIDE_A, None)
            self.data["model"].set_fouced(SIDE_B, None)
        self._focusing = enable

    def on_focused(self, index):
        if not self._focusing:
            return

        column = index.column()
        if column == 1:
            # Diff section
            return

        side = SIDE_A if column == 0 else SIDE_B
        side_data = models.SIDE_A_DATA if column == 0 else models.SIDE_B_DATA

        selection_model = self.data["view"].selectionModel()
        selection = selection_model.selection()
        selected = index in selection.indexes()

        if selected:
            node = index.data(models.ComparerModel.ItemRole)
            data = node.get(side_data)
            index = self.data["proxy"].mapToSource(index) if data else None
            self.data["model"].set_fouced(side, index)
        else:
            data = None
            self.data["model"].set_fouced(side, None)

        self.picked.emit(side, data)
        self.update()


class FocusComparing(QtWidgets.QWidget):

    focus_enabled = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(FocusComparing, self).__init__(parent=parent)

        widget = pindict.to_pindict({
            "overallDiff": {
                "main": QtWidgets.QGroupBox("Compare Features"),
                "name": {
                    "main": QtWidgets.QWidget(),
                    "icon": QtWidgets.QLabel(),
                    "label": QtWidgets.QLabel("Hierarchy"),
                    "status": QtWidgets.QLabel("--"),
                },
                "id": {
                    "main": QtWidgets.QWidget(),
                    "icon": QtWidgets.QLabel(),
                    "label": QtWidgets.QLabel("Avalon Id"),
                    "status": QtWidgets.QLabel("--"),
                },
                "mesh": {
                    "main": QtWidgets.QWidget(),
                    "icon": QtWidgets.QLabel(),
                    "label": QtWidgets.QLabel("Mesh"),
                    "status": QtWidgets.QLabel("--"),
                },
                "uv": {
                    "main": QtWidgets.QWidget(),
                    "icon": QtWidgets.QLabel(),
                    "label": QtWidgets.QLabel("UV"),
                    "status": QtWidgets.QLabel("--"),
                },
            },
            "featureMenu": {
                "main": QtWidgets.QWidget(),
                "label": QtWidgets.QLabel("Focus On"),
                "list": QtWidgets.QComboBox(),
            },
            "focus": {
                "view": QtWidgets.QTreeView(),
                "model": models.FocusModel(),
                "pathDelegate": delegates.PathTextDelegate(),
            }
        })

        with widget.pin("overallDiff") as diff:
            layout = QtWidgets.QVBoxLayout(diff["main"])

            for key in ["name", "id", "mesh", "uv"]:
                with widget.pin("overallDiff." + key) as feature:
                    lay = QtWidgets.QHBoxLayout(feature["main"])
                    lay.addWidget(feature["label"])
                    lay.addSpacing(8)
                    lay.addWidget(feature["icon"])
                    lay.addSpacing(12)
                    lay.addWidget(feature["status"], stretch=True)

                    feature["label"].setFixedWidth(60)
                    feature["label"].setAlignment(QtCore.Qt.AlignRight)

                    icon = delegates.FEATURE_ICONS[key]
                    pixmap = lib.icon(icon, models.COLOR_DARK).pixmap(16, 16)
                    feature["icon"].setPixmap(pixmap)

                layout.addWidget(feature["main"])
                layout.addSpacing(-16)
            layout.addSpacing(16)
            layout.setContentsMargins(0, 0, 0, 0)

        with widget.pin("featureMenu") as menu:
            layout = QtWidgets.QHBoxLayout(menu["main"])
            layout.addWidget(menu["label"])
            layout.addWidget(menu["list"])
            layout.addStretch()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addSpacing(-16)
        layout.addWidget(widget["overallDiff"]["main"])
        layout.addSpacing(-8)
        layout.addWidget(widget["featureMenu"]["main"])
        layout.addSpacing(-8)
        layout.addWidget(widget["focus"]["view"])

        # Init
        with widget.pin("featureMenu") as menu:
            menu["list"].addItem(" Hierarchy", "longName")
            menu["list"].addItem(" Avalon Id", "avalonId")
            menu["list"].addItem(" Full Path", "fullPath")
            menu["list"].addItem(" Mesh", "points")
            menu["list"].addItem(" UV", "uvmap")

        with widget.pin("focus") as focus:
            focus["view"].setModel(focus["model"])
            focus["view"].setItemDelegateForColumn(1, focus["pathDelegate"])
            focus["view"].setHeaderHidden(True)
            focus["view"].setUniformRowHeights(True)
            focus["view"].setAlternatingRowColors(False)
            focus["view"].setIndentation(6)
            focus["view"].setStyleSheet("""
                QTreeView::item{
                    padding: 2px 1px;
                    border: 0px;
                }
            """)
            focus["view"].setSelectionMode(focus["view"].NoSelection)
            height = focus["view"].sizeHintForRow(0) * 2 + 4  # MagicNum
            focus["view"].setFixedHeight(height)
            focus["view"].setColumnWidth(0, 28)

        self.widget = widget
        self._focusing = False

        # Connect
        with widget.pin("featureMenu") as menu:
            menu["list"].currentIndexChanged.connect(self.on_feature_changed)
        self.focus_enabled.connect(self.on_focus_enabled)

    def on_focus_enabled(self, enable):
        if not enable:
            self.widget["focus"]["model"].reset_sides()
            self.update()  # Reset
        self._focusing = enable

    def on_feature_changed(self, index=None):
        with self.widget.pin("featureMenu.list") as menu:
            feature = menu.currentData()
        with self.widget.pin("focus") as focus:
            focus["model"].set_focus(feature)

    def on_picked(self, side, data=None):
        if not self._focusing:
            return

        with self.widget.pin("focus") as focus:
            data = data or dict()
            focus["model"].set_side(side, data)
        # Compare
        self.update()
        self.on_feature_changed()

    def update(self):
        with self.widget.pin("focus") as focus:
            node_A = focus["model"].nodes[SIDE_A]
            node_B = focus["model"].nodes[SIDE_B]

        def related(this, that):
            return this == that or this.endswith(that) or that.endswith(this)

        def equal(this, that):
            return this == that

        features = [
            ("name", "longName", related),
            ("id", "avalonId", equal),
            ("mesh", "points", equal),
            ("uv", "uvmap", equal),
        ]

        for feature, key, compare in features:
            with self.widget.pin("overallDiff." + feature) as widget:
                fet_A = node_A.get(key)
                fet_B = node_B.get(key)

                if fet_A and fet_B:
                    if compare(fet_A, fet_B):
                        status = "Match"
                        color = models.COLOR_BRIGHT
                    else:
                        status = "Not Match"
                        color = models.COLOR_DANGER
                else:
                    status = "--"
                    color = models.COLOR_DARK

                icon = delegates.FEATURE_ICONS[feature]
                pixmap = lib.icon(icon, color).pixmap(16, 16)
                widget["icon"].setPixmap(pixmap)
                widget["status"].setText(status)
