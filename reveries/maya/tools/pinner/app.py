
import sys
from maya import cmds
from avalon import style
from avalon.tools import lib
from avalon.vendor.Qt import QtWidgets, QtCore
from avalon.vendor import qtawesome
from reveries.maya import capsule, lib as maya_lib

module = sys.modules[__name__]
module.window = None


cmds.loadPlugin("matrixNodes", quiet=True)


def bake_center(node, time=None):
    center_name = node + "_bboxC_PIN1"

    with capsule.delete_after() as delete_bin:
        bbox_min = cmds.spaceLocator(name="bbox_min")[0]
        bbox_max = cmds.spaceLocator(name="bbox_max")[0]
        bbox_center = cmds.group(empty=True, world=True, name=center_name)

        cmds.connectAttr(node + ".boundingBoxMin", bbox_min + ".translate")
        cmds.connectAttr(node + ".boundingBoxMax", bbox_max + ".translate")

        constrainer = cmds.pointConstraint(bbox_min, bbox_max,
                                           bbox_center,
                                           maintainOffset=False)
        # Fall back to time slider range if `time` is None
        if time is None:
            start = cmds.playbackOptions(query=True, minTime=True)
            end = cmds.playbackOptions(query=True, maxTime=True)
        else:
            start, end = time
        # Bake one frame more, if frame range is single frame
        if end == start:
            end += 1
        # Bake
        with capsule.keytangent_default(in_tangent_type="auto",
                                        out_tangent_type="auto"):
            print(start, end)
            cmds.bakeResults(bbox_center,
                             simulation=True,
                             disableImplicitControl=True,
                             shape=False,
                             sampleBy=1.0,
                             time=(start, end))

        delete_bin.extend([bbox_min, bbox_max] + constrainer)

    return bbox_center


def constraint_matrix(subject, target):
    out_name = "out_PIN1"
    out = cmds.group(empty=True, world=True, name=out_name)
    adder = cmds.createNode("addMatrix")
    decomposer = cmds.createNode("decomposeMatrix")

    cmds.connectAttr(subject + ".parentInverseMatrix",
                     adder + ".matrixIn[0]")
    cmds.connectAttr(target + ".worldMatrix",
                     adder + ".matrixIn[1]")
    cmds.connectAttr(adder + ".matrixSum",
                     decomposer + ".inputMatrix")
    cmds.connectAttr(decomposer + ".outputTranslate",
                     out + ".translate")
    return out


def pin(controller, pinner, geometry, time=None):
    tracer = bake_center(geometry, time)
    neutralizer = constraint_matrix(tracer, pinner)
    constraint = cmds.pointConstraint(neutralizer,
                                      controller,
                                      maintainOffset=False)[0]

    container = "__PINS__"
    if not cmds.objExists(container):
        cmds.group(empty=True, world=True, name=container)
    cmds.parent([tracer, neutralizer], container)

    maya_lib.connect_message(pinner, tracer, "pinner")
    maya_lib.connect_message(pinner, neutralizer, "pinner")
    maya_lib.connect_message(pinner, constraint, "pinner")


def unpin(pinner):
    source = pinner + ".message"
    connections = cmds.listConnections(source,
                                       source=False,
                                       destination=True,
                                       plugs=True)
    to_delete = list()
    for conn in connections:
        node, attr = conn.rsplit(".", 1)
        if attr == "pinner":
            to_delete.append(node)
    cmds.delete(to_delete)


class Window(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(Window, self).__init__(parent=parent)

        icon = qtawesome.icon("fa.map-pin", color="#E74C3C")
        unlink = qtawesome.icon("fa.chain-broken", color="#DFDFDF")

        self.setWindowIcon(icon)
        self.setWindowTitle("Pinner")
        self.setWindowFlags(QtCore.Qt.Window)

        widgets = {
            "pin": QtWidgets.QWidget(),
            "addPinBtn": QtWidgets.QPushButton("Create/Add Pin"),
            "pinName": QtWidgets.QLineEdit(),

            "ref": QtWidgets.QWidget(),
            "setReference": QtWidgets.QPushButton("Set Reference"),
            "refName": QtWidgets.QLineEdit(),

            "tar": QtWidgets.QWidget(),
            "setTarget": QtWidgets.QPushButton("Set Target"),
            "tarName": QtWidgets.QLineEdit(),

            "btm": QtWidgets.QWidget(),
            "runBtn": QtWidgets.QPushButton(icon, ""),
            "unlinkBtn": QtWidgets.QPushButton(unlink, ""),
        }

        widgets["addPinBtn"].setFixedWidth(160)
        widgets["setReference"].setFixedWidth(160)
        widgets["setTarget"].setFixedWidth(160)
        widgets["runBtn"].setFixedWidth(80)

        widgets["pinName"].setPlaceholderText(
            "A transform node to pin onto, default is a locator")
        widgets["refName"].setPlaceholderText(
            "Set motion reference object, like character's main geometry")
        widgets["tarName"].setPlaceholderText(
            "A transform node to be pinned, e.g. a rig controller")

        layout = QtWidgets.QHBoxLayout(widgets["pin"])
        layout.addWidget(widgets["addPinBtn"])
        layout.addWidget(widgets["pinName"], stretch=True)
        layout.setContentsMargins(0, 0, 0, 0)
        layout = QtWidgets.QHBoxLayout(widgets["ref"])
        layout.addWidget(widgets["setReference"])
        layout.addWidget(widgets["refName"], stretch=True)
        layout.setContentsMargins(0, 0, 0, 0)
        layout = QtWidgets.QHBoxLayout(widgets["tar"])
        layout.addWidget(widgets["setTarget"])
        layout.addWidget(widgets["tarName"], stretch=True)
        layout.setContentsMargins(0, 0, 0, 0)
        layout = QtWidgets.QHBoxLayout(widgets["btm"])
        layout.addStretch()
        layout.addWidget(widgets["runBtn"])
        layout.addWidget(widgets["unlinkBtn"])
        layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(widgets["pin"])
        layout.addWidget(widgets["ref"])
        layout.addWidget(widgets["tar"])
        layout.addStretch()
        layout.addWidget(widgets["btm"])

        # Connect
        widgets["addPinBtn"].clicked.connect(self.on_add_pin_clicked)
        widgets["setReference"].clicked.connect(self.on_set_ref_clicked)
        widgets["setTarget"].clicked.connect(self.on_set_target_clicked)
        widgets["runBtn"].clicked.connect(self.on_run_clicked)
        widgets["unlinkBtn"].clicked.connect(self.on_unlink_clicked)

        self.widgets = widgets
        self.resize(560, 150)

    def on_add_pin_clicked(self):
        selected = cmds.ls(sl=True, type="transform")
        if selected:
            pin = selected[0]
        else:
            pin = cmds.spaceLocator(name="pin1")[0]
        self.widgets["pinName"].setText(pin)

    def on_set_ref_clicked(self):
        selected = cmds.ls(sl=True, type="transform")
        if selected:
            ref = selected[0]
        else:
            raise Exception("No motion reference selected.")
        self.widgets["refName"].setText(ref)

    def on_set_target_clicked(self):
        selected = cmds.ls(sl=True, type="transform")
        if selected:
            tar = selected[0]
        else:
            raise Exception("No target transform node selected.")
        self.widgets["tarName"].setText(tar)

    def on_run_clicked(self):
        pinner = self.widgets["pinName"].text()
        geometry = self.widgets["refName"].text()
        controller = self.widgets["tarName"].text()
        pin(controller, pinner, geometry)

    def on_unlink_clicked(self):
        pinner = self.widgets["pinName"].text()
        if cmds.objExists(pinner):
            unpin(pinner)
        else:
            raise Exception("Pinner %s not exists." % pinner)


def show():
    """Display Main GUI"""
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
        window = Window(parent=mainwindow)
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window
