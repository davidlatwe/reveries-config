import sys
import time
import logging

from avalon import style
from avalon.tools import lib
from avalon.vendor.Qt import QtWidgets, QtCore

from maya import cmds
import maya.OpenMaya                # old api for MFileIO
import maya.api.OpenMaya as om

from . import widgets
from . import commands

module = sys.modules[__name__]
module.window = None


class App(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.log = logging.getLogger(__name__)

        # Store callback references
        self._callbacks = []

        filename = commands.get_workfile()

        self.setObjectName("lookManager")
        self.setWindowTitle("Look Manager 1.3.0 - [{}]".format(filename))
        self.setWindowFlags(QtCore.Qt.Window)
        self.setParent(parent)

        # Force to delete the window on close so it triggers
        # closeEvent only once. Otherwise it's retriggered when
        # the widget gets garbage collected.
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.resize(680, 400)

        self.setup_ui()

        self.setup_connections()

        # Force refresh check on initialization
        self._on_renderlayer_switch()

    def setup_ui(self):
        """Build the UI"""

        # Assets (left)
        asset_outliner = widgets.AssetOutliner()

        # Looks (right)
        looks_widget = QtWidgets.QWidget()
        looks_layout = QtWidgets.QVBoxLayout(looks_widget)
        # Sub widgets and layouts
        db_looks_widget = QtWidgets.QWidget()
        db_looks_layout = QtWidgets.QVBoxLayout(db_looks_widget)
        loaded_looks_widget = QtWidgets.QWidget()
        loaded_looks_layout = QtWidgets.QVBoxLayout(loaded_looks_widget)

        # Database look overview
        look_outliner = widgets.LookOutliner()
        # Scene look overview
        loaded_look_outliner = widgets.LoadedLookOutliner()
        # Button and checkBox
        overload_chk = QtWidgets.QCheckBox("Overload Looks")
        remove_unused_btn = QtWidgets.QPushButton("Remove Unused Looks")

        db_looks_layout.addWidget(look_outliner)
        db_looks_layout.addWidget(overload_chk)
        loaded_looks_layout.addWidget(loaded_look_outliner)

        # Look Splitter
        look_splitter = QtWidgets.QSplitter()
        look_splitter.setOrientation(QtCore.Qt.Vertical)
        look_splitter.setStyleSheet("QSplitter{ border: 0px; }")
        look_splitter.addWidget(db_looks_widget)
        look_splitter.addWidget(loaded_looks_widget)
        look_splitter.setSizes([200, 120])

        looks_layout.addWidget(look_splitter)
        looks_layout.addWidget(remove_unused_btn)

        # Footer
        status = QtWidgets.QStatusBar()
        status.setSizeGripEnabled(False)
        status.setFixedHeight(25)
        warn_layer = QtWidgets.QLabel("Current Layer is not "
                                      "defaultRenderLayer")
        warn_layer.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        warn_layer.setStyleSheet("color: #DD5555; font-weight: bold;")
        warn_layer.setFixedHeight(25)

        footer = QtWidgets.QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addWidget(status)
        footer.addWidget(warn_layer)

        # Build up widgets
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_splitter = QtWidgets.QSplitter()
        main_splitter.setStyleSheet("QSplitter{ border: 0px; }")
        main_splitter.addWidget(asset_outliner)
        main_splitter.addWidget(looks_widget)
        main_splitter.setSizes([350, 280])
        main_layout.addWidget(main_splitter)
        main_layout.addLayout(footer)

        # Set column width
        asset_outliner.view.setColumnWidth(0, 200)
        look_outliner.view.setColumnWidth(0, 140)  # "label" column
        look_outliner.view.setColumnWidth(1, 60)   # "version" column
        look_outliner.view.setColumnWidth(2, 50)   # "match" column

        loaded_look_outliner.view.setColumnWidth(0, 140)  # "label" column
        loaded_look_outliner.view.setColumnWidth(1, 60)   # "No." column
        loaded_look_outliner.view.setColumnWidth(2, 50)   # "match" column

        # Open widgets
        self.asset_outliner = asset_outliner
        self.look_outliner = look_outliner
        self.loaded_look_outliner = loaded_look_outliner
        self.status = status
        self.warn_layer = warn_layer

        # Buttons and CheckBoxes
        self.remove_unused = remove_unused_btn
        self.overload = overload_chk

    def setup_connections(self):
        """Connect interactive widgets with actions"""

        self.asset_outliner.selection_changed.connect(
            self.on_asset_selection_changed)

        self.asset_outliner.refreshed.connect(
            lambda: self.echo("Loaded assets.."))

        self.look_outliner.menu_apply_action.connect(self.on_process_selected)
        self.look_outliner.menu_apply_via_uv_action.connect(
            lambda: self.on_process_selected(uv=True)
        )
        self.loaded_look_outliner.menu_apply_action.connect(
            lambda: self.on_process_selected(use_loaded=True)
        )
        self.loaded_look_outliner.menu_apply_via_uv_action.connect(
            lambda: self.on_process_selected(use_loaded=True, uv=True)
        )

        self.remove_unused.clicked.connect(commands.remove_unused_looks)

        # Maya renderlayer switch callback
        callback = om.MEventMessage.addEventCallback(
            "renderLayerManagerChange",
            self._on_renderlayer_switch
        )
        self._callbacks.append(callback)

    def closeEvent(self, event):

        # Delete callbacks
        for callback in self._callbacks:
            om.MMessage.removeCallback(callback)

        return super(App, self).closeEvent(event)

    def _on_renderlayer_switch(self, *args):
        """Callback that updates on Maya renderlayer switch"""

        if maya.OpenMaya.MFileIO.isNewingFile():
            # Don't perform a check during file open or file new as
            # the renderlayers will not be in a valid state yet.
            return

        layer = cmds.editRenderLayerGlobals(query=True,
                                            currentRenderLayer=True)
        if layer != "defaultRenderLayer":
            self.warn_layer.show()
        else:
            self.warn_layer.hide()

    def echo(self, message):
        self.status.showMessage(message, 6000)

    def on_asset_selection_changed(self):
        """Get selected items from asset loader and fill look outliner"""

        items = self.asset_outliner.get_selected_items()
        self.look_outliner.clear()
        self.loaded_look_outliner.clear()
        self.look_outliner.add_items(items)
        self.loaded_look_outliner.add_items(items)

    def on_process_selected(self, use_loaded=False, uv=False):
        """Process all selected looks for the selected assets"""

        assets = self.asset_outliner.get_selected_items()
        assert assets, "No asset selected"

        if use_loaded:
            look_outliner = self.loaded_look_outliner
            look_getter = commands.get_loaded_look
            look_key = "loadedLooks"
            match_tag = "No."
            match_key = "No."
        else:
            look_outliner = self.look_outliner
            look_getter = commands.load_look
            look_key = "looks"
            match_tag = "subset"
            match_key = "name"

        overload = self.overload.isChecked()

        # Collect the looks we want to apply (by name)
        look_items = look_outliner.get_selected_items()
        looks = {look[match_tag] for look in look_items}

        asset_nodes = self.asset_outliner.get_nodes()

        start = time.time()
        for i, ((asset, namespace), item) in enumerate(asset_nodes.items()):

            # Label prefix
            prefix = "({}/{})".format(i + 1, len(asset_nodes))
            asset = "[{}] {}".format(asset, namespace)

            # Assign the first matching look relevant for this asset
            # (since assigning multiple to the same nodes makes no sense)
            assign_look = next((subset for subset in item[look_key]
                                if subset[match_key] in looks), None)
            if not assign_look:
                self.echo("{} No matching selected "
                          "look for {}".format(prefix, asset))
                continue

            look = look_getter(assign_look, overload=overload)
            self.echo("{} Assigning {} to {}\t".format(prefix,
                                                       look["name"],
                                                       asset))
            # Assign look
            namespaces = item.get("namespace", item["namespaces"])
            commands.assign_look(namespaces=namespaces,
                                 look=look,
                                 via_uv=uv)

        end = time.time()

        self.echo("Finished assigning.. ({0:.3f}s)".format(end - start))

        if overload:
            self.overload.setChecked(False)


def show():
    """Display Loader GUI

    Arguments:
        debug (bool, optional): Run loader in debug-mode,
            defaults to False

    """

    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    # Get Maya main window
    top_level_widgets = QtWidgets.QApplication.topLevelWidgets()
    mainwindow = next(widget for widget in top_level_widgets
                      if widget.objectName() == "MayaWindow")

    with lib.application():
        window = App(parent=mainwindow)
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window
