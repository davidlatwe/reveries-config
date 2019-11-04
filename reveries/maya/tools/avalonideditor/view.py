
from avalon.vendor.Qt import QtWidgets, QtCore

from . import model, delegate


class SelectionOutline(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(SelectionOutline, self).__init__(parent=parent)

        self.model = model.SelectionModel()
        proxy = QtCore.QSortFilterProxyModel()
        proxy.setSourceModel(self.model)

        view = QtWidgets.QTreeView()
        view.setIndentation(20)
        view.setStyleSheet("""
            QTreeView::item{
                padding: 4px 1px;
                border: 0px;
            }
        """)
        view.setAllColumnsShowFocus(True)
        view.setAlternatingRowColors(True)
        view.setSortingEnabled(True)
        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.sortByColumn(1, QtCore.Qt.AscendingOrder)
        view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # Delegate
        time_delegate = delegate.PrettyTimeDelegate()
        column = self.model.Columns.index("time")
        view.setItemDelegateForColumn(column, time_delegate)

        view.setModel(proxy)
        view.setColumnWidth(0, 100)
        view.setColumnWidth(1, 140)
        view.setColumnWidth(2, 200)
        view.setColumnWidth(3, 200)
        view.setColumnWidth(4, 70)
        self.view = view
        self.proxy = proxy

        # (TODO)
        # Get all nodes
        # Get selected nodes
        # Dynamic selecting (If this enabled, dim out above two. Default off)
        # "Freeze List" will not be needed

        freezer = QtWidgets.QCheckBox("Freeze List")

        # (TODO)
        # These three not implemented
        include_hierarchy = QtWidgets.QCheckBox("Include Hierarchy")
        hide_referenced = QtWidgets.QCheckBox("Hide Referenced")
        refresh = QtWidgets.QPushButton("Refresh")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(freezer)
        layout.addWidget(include_hierarchy)
        layout.addWidget(hide_referenced)
        layout.addWidget(self.view)
        layout.addWidget(refresh)

        self.setLayout(layout)

        self.data = {
            "delegates": {
                "time": time_delegate,
            }
        }

        self.view.customContextMenuRequested.connect(self.on_menu)
        freezer.stateChanged.connect(self.on_freezed)

    def start(self):
        self.model.stop()
        self.model.on_selected()
        self.model.listen()

    def stop(self):
        self.model.stop()

    def on_freezed(self, state):
        self.model._selection_freezed = state

    def on_menu(self, point):
        point_index = self.view.indexAt(point)
        if not point_index.isValid():
            return

        menu = QtWidgets.QMenu(self)

        select_action = QtWidgets.QAction("Select..", menu)
        select_action.triggered.connect(self.act_select)

        menu.addAction(select_action)

        # Show the context action menu
        global_point = self.view.mapToGlobal(point)
        # Tweak menu position so user can directly hit select action without
        # moving cursor much.
        global_point.setX(global_point.x() - 70)
        global_point.setY(global_point.y() + 10)
        action = menu.exec_(global_point)
        if not action:
            return

    def act_select(self):
        selection_model = self.view.selectionModel()
        selection = selection_model.selection()
        source_selection = self.proxy.mapSelectionToSource(selection)
        self.model.select_back(source_selection.indexes())


class Diagnose(QtWidgets.QWidget):
    pass
