import os
import sys
import subprocess
from functools import partial

import avalon.api
from avalon import io
from reveries.plugins import PackageLoader

from avalon.vendor.Qt import QtWidgets
from avalon.vendor.Qt import QtCore
from avalon.vendor.Qt import QtGui

from avalon.vendor import qtawesome
from avalon import style


def update_subset_group(shot_id, update_data):
    for group, layers in update_data.items():
        for layer_name in layers:
            subset_filter = {
                'type': 'subset',
                'name': layer_name,
                'parent': avalon.io.ObjectId(shot_id)
            }

            subset_data = [s for s in io.find(subset_filter)]

            if subset_data:
                subset_data = subset_data[0]

                if subset_data["data"].get("subsetGroup", "") != group:
                    update = {
                        "data.subsetGroup": group
                    }
                    io.update_many(subset_filter, update={"$set": update})


def env_embedded_path(path):
    """Embed environment var `$AVALON_PROJECTS` and `$AVALON_PROJECT` into path

    This will ensure reference or cache path resolvable when project root
    moves to other place.

    """
    path = path.replace(
        "$AVALON_PROJECTS", avalon.api.registered_root()
    )
    path = path.replace(
        "$AVALON_PROJECT", avalon.Session["AVALON_PROJECT"]
    )
    return path


class EditFxPrim(PackageLoader, avalon.api.Loader):
    """Edit fx primitive."""

    label = "Edit Fx Primitive"
    order = -15
    icon = "pencil"
    color = "#56a6db"

    families = [
        "reveries.fx.usd"
    ]

    representations = [
        "USD",
    ]

    def _file_path(self, representation):
        file_name = representation["data"]["entryFileName"]
        entry_path = os.path.join(self.package_path, file_name)

        if not os.path.isfile(entry_path):
            raise IOError("File Not Found: {!r}".format(entry_path))

        return env_embedded_path(entry_path)

    def load(self, context, name, namespace, data):
        # Get usd file
        representation = context["representation"]
        entry_path = self._file_path(representation)
        usd_file = os.path.expandvars(entry_path).replace("\\", "/")

        if not usd_file:
            directory = self.package_path
            files = os.listdir(directory)
            if not files:
                self.log.info('No usd file found in : {}'.format(directory))
                return

            usd_file = os.path.join(directory, files[0])

        print("\n\n")
        print("usd_file: ", usd_file)

        self.shot_id = context["asset"]["_id"]
        self.shot_name = context["asset"]["name"]

        self.open_edit_ui()

    def open_edit_ui(self):
        module = sys.modules[__name__]
        module.window = None

        window = FxUSDLayerWidget(
            shot_id=self.shot_id, shot_name=self.shot_name)
        window.show()

        module.window = window


class FxUSDLayerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, shot_id=None, shot_name=None):
        super(FxUSDLayerWidget, self).__init__(parent=parent)

        self.shot_id = shot_id
        self.shot_name = shot_name

        self.has_trash_item = False
        self.currently_item = []
        self.trash_item = []

        self._init_ui()

        self.resize(450, 550)
        self.setWindowIcon(qtawesome.icon("fa.pencil", color="#1590fb"))
        self.setWindowTitle("Edit Fx Primitive")
        self.setStyleSheet(style.load_stylesheet())

    def _get_fx_layer_data(self):
        """
        fx_layer_data = {
            "fxlayerRBD_Bottle": {
                "usd_type": "Sublayer",
                "subsetGroup": "Fx"
            },
            "fxlayerPYRO_SIM": {
                "usd_type": "Reference",
                "subsetGroup": "Fx"
            },
            "fxlayerTERRAIN_OUT": {
                "usd_type": "Sublayer",
                "subsetGroup": "Fx"
            },
            "fxlayerTERRAIN_IN": {
                "usd_type": "Sublayer",
                "subsetGroup": "Fx"
            }
        }
        """
        self.fx_layer_data = {}
        subset_filter = {
            'type': 'subset',
            'data.families': r'reveries.fx.layer_prim',
            'parent': avalon.io.ObjectId(self.shot_id)
        }
        subset_data = [s for s in io.find(subset_filter)]
        for _data in subset_data:
            _filter = {
                "type": "version",
                "parent": _data["_id"]
            }
            version_data = io.find_one(_filter, sort=[("name", -1)])
            if version_data:
                self.fx_layer_data[_data["name"]] = {
                    "subsetGroup": _data["data"]["subsetGroup"],
                    "usd_type": version_data["data"].get("usd_type", "")
                }

    def _init_ui(self):
        self._get_fx_layer_data()

        self.tree_currently = QtWidgets.QTreeWidget()
        self.tree_trash = QtWidgets.QTreeWidget()

        for _tree_widget in [self.tree_currently, self.tree_trash]:
            _tree_widget.setColumnCount(3)
            _tree_widget.setHeaderLabels(['Fx Layer Name', 'USD Type', ''])
            _tree_widget.header().setSectionResizeMode(
                QtWidgets.QHeaderView.ResizeToContents
            )

            _tree_widget.headerItem().setTextAlignment(0, QtCore.Qt.AlignCenter)
            _tree_widget.headerItem().setTextAlignment(1, QtCore.Qt.AlignCenter)

        currently_label = QtWidgets.QLabel("Currently Version:")
        trash_label = QtWidgets.QLabel("In Trash Bin:")

        # Generate currently version widget
        for _layer_name, _data in self.fx_layer_data.items():
            if _data["subsetGroup"] == "Fx":
                self.currently_item.append(_layer_name)
            elif _data["subsetGroup"] == "Trash Bin":
                self.has_trash_item = True
                self.trash_item.append(_layer_name)

        self.refresh_ui()

        pub_button = QtWidgets.QPushButton("RePublish")
        pub_button.clicked.connect(self.re_publish)

        # Cancel button
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close_win)

        self.progressbar = QtWidgets.QProgressBar()
        self.progressbar.setRange(0, 10)
        self.progressbar.setVisible(0)

        # Widget layout
        btn_lay = QtWidgets.QHBoxLayout()
        btn_lay.addWidget(pub_button)
        btn_lay.addWidget(cancel_btn)

        _currently_widget = QtWidgets.QWidget()
        _currently_lay = QtWidgets.QVBoxLayout(_currently_widget)
        _currently_lay.addWidget(currently_label)
        _currently_lay.addWidget(self.tree_currently)

        self.trash_widget = QtWidgets.QWidget()
        _trash_lay = QtWidgets.QVBoxLayout(self.trash_widget)
        _trash_lay.addWidget(trash_label)
        _trash_lay.addWidget(self.tree_trash)
        self.trash_widget.setVisible(self.has_trash_item)

        _splitter = QtWidgets.QSplitter()
        _splitter.setOrientation(QtCore.Qt.Vertical)
        _splitter.addWidget(_currently_widget)
        _splitter.addWidget(self.trash_widget)
        _splitter.setStretchFactor(0, 65)
        _splitter.setStretchFactor(1, 35)

        main_lay = QtWidgets.QVBoxLayout()
        main_lay.addWidget(_splitter)
        main_lay.addWidget(self.progressbar)
        main_lay.addLayout(btn_lay)

        self.setLayout(main_lay)

    def re_publish(self):
        from reveries import utils
        from reveries.common.widgets.messagebox import MessageBoxWindow

        tmp_dir = utils.stage_dir()
        self.progressbar.setVisible(1)

        # === Update publish data === #
        self.progressbar.setValue(1)
        _data = {
            "Trash Bin": self.trash_item,
            "Fx": self.currently_item
        }
        update_subset_group(self.shot_id, _data)

        # === Republish Fx Primitive === #
        self.progressbar.setValue(3)
        publisher = RePublisFxPrimitive(self.shot_name, self.shot_id, tmp_dir)

        self.progressbar.setValue(6)
        publisher.export_fx_primitive()

        # ==== Done === #
        self.progressbar.setValue(7)
        if publisher.republish():
            self.progressbar.setValue(10)
            window = MessageBoxWindow(
                window_title='RePublish Fx Primitive',
                text='Publish done.',
                parent=self
            )
            window.setStyleSheet(style.load_stylesheet())
            window.show()

        self.progressbar.setValue(0)
        self.progressbar.setVisible(0)

    def refresh_ui(self):
        # Refresh trash tree widget
        i = self.tree_trash.topLevelItemCount()
        while i > -1:
            self.tree_trash.takeTopLevelItem(i)
            i -= 1

        for _name in self.trash_item:
            _item = self._tree_widget(
                _name, self.fx_layer_data[_name], self.tree_trash,
                self._to_reply,
                icon="reply"
            )

        # Refresh currently tree widget
        i = self.tree_currently.topLevelItemCount()
        while i > -1:
            self.tree_currently.takeTopLevelItem(i)
            i -= 1

        for _name in self.currently_item:
            _item = self._tree_widget(
                _name, self.fx_layer_data[_name], self.tree_currently,
                self._to_trash
            )

    def _to_trash(self, layer_name):
        if layer_name not in self.trash_item:
            self.trash_item.append(layer_name)
            self.currently_item.remove(layer_name)

        if self.trash_item:
            self.has_trash_item = True
            self.trash_widget.setVisible(self.has_trash_item)

            self.refresh_ui()

    def _to_reply(self, layer_name):
        if layer_name not in self.currently_item:
            self.currently_item.append(layer_name)
            self.trash_item.remove(layer_name)

        if self.currently_item:
            self.refresh_ui()

    def _tree_widget(
            self, _layer_name, _data, tree_widget, btn_func, icon="trash"):

        index_color = tree_widget.topLevelItemCount() + 1

        set_name_item = QtWidgets.QTreeWidgetItem()

        set_name_item.setText(0, _layer_name)
        set_name_item.setText(1, _data["usd_type"])

        self._set_item_background_color(index_color, set_name_item)

        # trash button
        _btn_widget = QtWidgets.QWidget()
        self._set_item_background_color2(index_color, _btn_widget)
        icon = qtawesome.icon("fa.{}".format(icon), color=style.colors.light)
        _btn = QtWidgets.QPushButton(icon, "")
        _btn.setFixedWidth(30)
        _btn.clicked.connect(partial(btn_func, _layer_name))

        _layer_lay = QtWidgets.QHBoxLayout(_btn_widget)
        _layer_lay.addWidget(_btn)

        tree_widget.addTopLevelItem(set_name_item)
        tree_widget.setItemWidget(set_name_item, 2, _btn_widget)

        return set_name_item

    def _set_item_background_color(self, index_color, _item):
        if index_color % 2 == 0:
            _item.setBackground(0, QtGui.QColor('#383838'))
            _item.setBackground(1, QtGui.QColor('#383838'))
            _item.setBackground(2, QtGui.QColor('#383838'))

    def _set_item_background_color2(self, index_color, _item):
        if index_color % 2 == 0:
            _item.setStyleSheet("background-color: #383838;")
        else:
            _item.setStyleSheet("background-color: #201F1F;")

    def close_win(self):
        self.close()


class RePublisFxPrimitive(object):
    def __init__(self, shot_name, shot_id, tmp_dir):
        self.tmp_dir = tmp_dir
        self.shot_name = shot_name
        self.shot_id = shot_id

    def export_fx_primitive(self):
        # === Get env === #
        project_root = avalon.api.Session["AVALON_PROJECTS"]
        project_name = avalon.api.Session["AVALON_PROJECT"]
        config_path = os.environ["CONFIG_ROOT"]

        # === Export Fx Primitive === #
        usdenv_bat = os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         "../../../../",
                         "reveries/tools/edit_fx_primitive/usdenv.bat")
        )
        usd_file = os.path.abspath(
            os.path.join(os.path.dirname(__file__),
                         "../../../../",
                         "reveries/tools/edit_fx_primitive/core.py")
        )

        cmd = [
            usdenv_bat,
            usd_file,
            self.shot_name, self.tmp_dir, project_name, project_root,
            config_path
        ]
        print("cmd: ", cmd)

        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate()
        print(out.decode('UTF-8'))

    def republish(self):
        from reveries.common.publish import publish_version, \
            publish_representation

        usd_file = os.path.join(self.tmp_dir, "fx_prim.usda")
        if os.path.exists(usd_file):
            _filter = {
                "type": "subset",
                "name": "fxPrim",
                "parent": avalon.io.ObjectId(self.shot_id)
            }
            subset_data = io.find_one(_filter)

            # Publish version
            version_id = publish_version.publish(subset_data["_id"])

            # Publish representation
            reps_data = {
                'entryFileName': 'fx_prim.usda',
            }
            publish_representation.publish(
                version_id, "USD", [usd_file],
                delete_source=True, data=reps_data
            )

        return True
