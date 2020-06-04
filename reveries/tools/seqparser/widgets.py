
import os
from avalon.vendor.Qt import QtWidgets, QtCore, QtGui, QtCompat
from avalon.vendor import qtawesome
from avalon.tools import models
from . import delegates


ExtendedSelection = QtWidgets.QAbstractItemView.ExtendedSelection


class SequenceWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(SequenceWidget, self).__init__(parent=parent)

        data = {
            "model": SequenceModel(),
            "proxy": QtCore.QSortFilterProxyModel(),
            "view": QtWidgets.QTreeView(),
            "fpatternDel": None,
            "nameDel": None,
            # "resolutionDel": None,
        }

        data["proxy"].setSourceModel(data["model"])
        data["view"].setModel(data["proxy"])
        data["fpatternDel"] = delegates.LineHTMLDelegate(data["view"])
        data["nameDel"] = delegates.NameEditDelegate()
        # data["resolutionDel"] = delegates.ResolutionDelegate()

        fpattern_delegate = data["fpatternDel"]
        column = data["model"].Columns.index("fpattern")
        data["view"].setItemDelegateForColumn(column, fpattern_delegate)

        name_delegate = data["nameDel"]
        column = data["model"].Columns.index("name")
        data["view"].setItemDelegateForColumn(column, name_delegate)

        # res_delegate = data["resolutionDel"]
        # column = data["model"].Columns.index("resolution")
        # data["view"].setItemDelegateForColumn(column, res_delegate)

        data["proxy"].setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        data["view"].setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        data["view"].setSelectionMode(ExtendedSelection)
        data["view"].setSortingEnabled(True)
        data["view"].sortByColumn(0, QtCore.Qt.AscendingOrder)
        data["view"].setAlternatingRowColors(True)
        data["view"].setAllColumnsShowFocus(True)
        data["view"].setIndentation(6)
        data["view"].setStyleSheet("""
            QTreeView::item{
                padding: 8px 1px;
                border: 0px;
            }
        """)

        header = data["view"].header()
        # Enforce the columns to fit the data (purely cosmetic)
        QtCompat.setSectionResizeMode(
            header, QtWidgets.QHeaderView.ResizeToContents)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(data["view"])
        layout.setContentsMargins(0, 0, 0, 0)

        data["view"].customContextMenuRequested.connect(self.on_context_menu)

        self.data = data

    def on_context_menu(self, point):
        view = self.data["view"]

        point_index = view.indexAt(point)
        if not point_index.isValid():
            return

        menu = QtWidgets.QMenu(view)
        # icon_res = qtawesome.icon("fa.film", color="gray")
        icon_dir = qtawesome.icon("fa.folder-open", color="gray")

        # res_act = QtWidgets.QAction(menu, icon=icon_res,
        #                             text="Set Resolution")
        # res_act.triggered.connect(self.action_set_resolution)

        dir_act = QtWidgets.QAction(menu, icon=icon_dir, text="Open Dir")
        dir_act.triggered.connect(self.action_open_dir)

        # menu.addAction(res_act)
        menu.addAction(dir_act)

        globalpos = view.mapToGlobal(point)
        menu.exec_(globalpos)

    def action_set_resolution(self):
        # Unused action
        dialog = QtWidgets.QDialog(self)
        editor = delegates.ResolutionEditor()
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(editor)

        view = self.data["view"]
        proxy = view.model()
        model = proxy.sourceModel()
        column = model.Columns.index("resolution")

        index = view.selectionModel().selectedRows(column)[0]
        index = proxy.mapToSource(index)
        editor.set_value(model.data(index, QtCore.Qt.DisplayRole))

        def set_res(value):
            for index in view.selectionModel().selectedRows(column):
                index = proxy.mapToSource(index)
                model.setData(index, value)

        editor.value_changed.connect(set_res)

        dialog.setWindowTitle("Set Resolution")
        dialog.exec_()

    def action_open_dir(self):
        view = self.data["view"]
        proxy = view.model()
        to_open = set()

        for index in view.selectionModel().selectedRows(0):
            index = proxy.mapToSource(index)
            item = index.internalPointer()
            dir_path = os.path.dirname(item["root"] + "/" + item["fpattern"])
            to_open.add(dir_path)

        for path in to_open:
            os.startfile(path)

    def set_stereo(self, vlaue):
        self.data["model"].set_stereo(vlaue)

    def add_sequences(self, sequences):
        model = self.data["model"]
        model.clear()
        for sequence in sequences:
            model.add_sequence(sequence)

    def collected(self, with_keys=None):
        with_keys = with_keys or list()
        sequences = list()
        root_index = QtCore.QModelIndex()
        for row in range(self.data["model"].rowCount(root_index)):
            index = self.data["model"].index(row, column=0, parent=root_index)
            item = index.internalPointer()
            if all(item.get(k) for k in with_keys):
                sequences.append(item)

        return sequences


class SequenceModel(models.TreeModel):

    Columns = [
        "fpattern",
        # "resolution",
        "name",
    ]

    HTMLTextRole = QtCore.Qt.UserRole + 10

    def __init__(self, parent=None):
        super(SequenceModel, self).__init__(parent)
        self._stereo = False
        self._stereo_icons = {
            "Left": qtawesome.icon("fa.bullseye", color="#FC3731"),
            "Right": qtawesome.icon("fa.bullseye", color="#53D8DF"),
            None: qtawesome.icon("fa.circle", color="#656565"),
        }

    def set_stereo(self, value):
        self._stereo = value

    def add_sequence(self, sequence):
        root_index = QtCore.QModelIndex()
        last = self.rowCount(root_index)

        self.beginInsertRows(root_index, last, last)

        item = models.Item()
        item.update(sequence)

        # Must have
        item["root"] = sequence["root"]
        item["fpattern"] = sequence["fpattern"]
        item["paddingStr"] = sequence["paddingStr"]
        # Optional
        item["name"] = sequence.get("name", "")
        # item["resolution"] = sequence.get("resolution")  # Should be (w, h)

        if self._stereo:

            def take_side(fpattern):
                if "Left" in fpattern:
                    return "Left", fpattern.replace("Left", "{stereo}")
                elif "Right" in fpattern:
                    return "Right", fpattern.replace("Right", "{stereo}")
                else:
                    return None, fpattern

            this_side, this_side_p = take_side(item["fpattern"])

            if this_side is not None:
                for row in reversed(range(last)):
                    index = self.index(row, column=0, parent=root_index)
                    other = index.internalPointer()
                    if other.get("stereoSide"):
                        # Paired
                        continue

                    other_side, other_side_p = take_side(other["fpattern"])
                    if other_side is None:
                        continue

                    if this_side != other_side and this_side_p == other_side_p:
                        item["stereoSide"] = this_side
                        item["stereoPattern"] = this_side_p
                        other["stereoSide"] = other_side
                        other["stereoPattern"] = other_side_p
                        break

        html_fpattern = "{dir}{head}{padding}{tail}"

        dir, fname = os.path.split(item["fpattern"])
        head, tail = fname.split(item["paddingStr"], 1)
        padding = item["paddingStr"]

        dir = "<span style=\"color:#666666\">%s/ </span>" % dir
        head = "<span style=\"color:#EEEEEE\">%s</span>" % head
        padding = "<span style=\"color:#666666\">%s</span>" % padding
        tail = "<span style=\"color:#999999\">%s</span>" % tail

        item["fpatternHTML"] = html_fpattern.format(dir=dir,
                                                    head=head,
                                                    padding=padding,
                                                    tail=tail)
        self.add_child(item)

        self.endInsertRows()

    def data(self, index, role):
        if not index.isValid():
            return

        if role == QtCore.Qt.FontRole:
            font = QtGui.QFont("Monospace")
            font.setStyleHint(QtGui.QFont.TypeWriter)
            return font

        if role == self.HTMLTextRole:
            node = index.internalPointer()
            return node["fpatternHTML"]

        # if role == QtCore.Qt.DisplayRole:
        #     if index.column() == self.Columns.index("resolution"):
        #         node = index.internalPointer()
        #         return node["resolution"] or (0, 0)

        if role == QtCore.Qt.DecorationRole:
            if index.column() == self.Columns.index("name"):
                if self._stereo:
                    node = index.internalPointer()
                    side = node.get("stereoSide")
                    return self._stereo_icons[side]

        return super(SequenceModel, self).data(index, role)

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        # Make the version column editable
        if index.column() in [self.Columns.index("fpattern"),
                              # self.Columns.index("resolution"), ]:
                              self.Columns.index("name"), ]:
            flags |= QtCore.Qt.ItemIsEditable

        return flags
