
import sys
import logging

from avalon import io, style
from avalon.tools import lib as tools_lib
from avalon.vendor.Qt import QtWidgets, QtCore

from . import views, lib
from .. import widgets
from ...lib import pindict


module = sys.modules[__name__]
module.window = None


main_logger = logging.getLogger("modeldiffer")
main_logger.setLevel(logging.INFO)

stream = logging.StreamHandler()
main_logger.addHandler(stream)


class Window(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(Window, self).__init__(parent=parent)

        self.setWindowIcon(lib.icon("share-alt-square", color="#EC905C"))
        self.setWindowTitle("Model Differ")
        self.setWindowFlags(QtCore.Qt.Window)

        page = {
            "tab": QtWidgets.QTabWidget(),
        }

        page["tab"].addTab(QtWidgets.QWidget(), "+")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(page["tab"])

        # Connect
        page["tab"].currentChanged.connect(self.on_tab_changed)

        # Init
        self.page = page
        self.create_tab()
        self.resize(840, 720)

    def on_tab_changed(self, index):
        if index != 0:
            return
        self.create_tab()

    def create_tab(self):
        widget = pindict.to_pindict({
            "main": QtWidgets.QWidget(),

            "top": {
                "main": QtWidgets.QWidget(),
                "label": QtWidgets.QLabel("Table Name:"),
                "line": QtWidgets.QLineEdit(),
                "nameChk": QtWidgets.QCheckBox("Show Namespace"),
            },

            "ctrl": {
                "tabs": {
                    "main": QtWidgets.QTabWidget(),
                    "focus": views.FocusComparing(),
                    "select": {
                        "main": QtWidgets.QWidget(),
                        "selectorA": views.SelectorWidget(side=views.SIDE_A),
                        "selectorB": views.SelectorWidget(side=views.SIDE_B),
                    },
                },
            },

            "table": {
                "tabs": {
                    "main": QtWidgets.QTabWidget(),
                    "comparer": views.ComparingTable(),
                },
            },

            "statusLine": widgets.StatusLineWidget(main_logger, self),
        })

        with widget.pin("top") as top:
            layout = QtWidgets.QHBoxLayout(top["main"])
            layout.addWidget(top["label"])
            layout.addWidget(top["line"])
            layout.addWidget(top["nameChk"])

        with widget.pin("ctrl.tabs.select") as selectors:
            layout = QtWidgets.QHBoxLayout(selectors["main"])
            layout.addWidget(selectors["selectorA"])
            layout.addSpacing(-12)
            layout.addWidget(selectors["selectorB"])
            layout.setContentsMargins(2, 2, 2, 2)

        with widget.pin("ctrl.tabs") as ctrl:
            icon_1 = lib.icon("hand-o-right", "white")
            icon_2 = lib.icon("bullseye", "#BEBEBE")
            ctrl["main"].addTab(ctrl["select"]["main"], icon_1, "Select")
            ctrl["main"].addTab(ctrl["focus"], icon_2, "Focus")
            ctrl["main"].setTabPosition(QtWidgets.QTabWidget.West)

        with widget.pin("table.tabs") as table:
            icon = lib.icon("adjust", "#BEBEBE")
            table["main"].addTab(table["comparer"], icon, "Compare")
            table["main"].setTabPosition(QtWidgets.QTabWidget.West)

        layout = QtWidgets.QVBoxLayout(widget["main"])
        layout.addWidget(widget["top"]["main"])
        layout.addWidget(widget["ctrl"]["tabs"]["main"])
        layout.addWidget(widget["table"]["tabs"]["main"], stretch=True)
        layout.addWidget(widget["statusLine"])
        layout.setContentsMargins(4, 4, 4, 4)

        tab = self.page["tab"]

        # Add Tab
        name = "New %d" % tab.count()
        index = tab.addTab(widget["main"], name)
        tab.setCurrentIndex(index)
        widget["top"]["line"].setText(name)

        # Connect
        with widget.pin("table.tabs") as table:
            with widget.pin("ctrl.tabs.select") as selectors:
                selectors["selectorA"].connect_comparer(table["comparer"])
                selectors["selectorB"].connect_comparer(table["comparer"])

            with widget.pin("ctrl.tabs.focus") as focus:
                table["comparer"].item_picked.connect(focus.on_picked)

            with widget.pin("top") as top:
                top["nameChk"].stateChanged.connect(
                    table["comparer"].on_name_mode_changed)
                top["line"].textChanged.connect(
                    lambda text: tab.setTabText(index, text))


def register_host_profiler(method):
    lib.profile_from_host = method


def register_host_selector(method):
    lib.select_from_host = method


def show():
    """Display Main GUI"""
    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    with tools_lib.application():
        window = Window(parent=None)
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window


def cli():
    io.install()
    show()
