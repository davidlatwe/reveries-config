
import sys
import logging

from avalon import style
from avalon.tools import lib
from avalon.vendor.Qt import QtWidgets, QtCore
from avalon.vendor import qtawesome

from . import views
from .. import widgets


module = sys.modules[__name__]
module.window = None


main_logger = logging.getLogger("modeldiffer")
main_logger.setLevel(logging.INFO)

stream = logging.StreamHandler()
main_logger.addHandler(stream)


class Window(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(Window, self).__init__(parent=parent)

        self.setWindowIcon(qtawesome.icon("fa.share-alt-square",
                                          color="#EC905C"))
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
        panel = {
            "body": QtWidgets.QWidget(),
            "top": QtWidgets.QWidget(),
            "control": QtWidgets.QWidget(),
            "table": QtWidgets.QWidget(),
        }

        widget = {
            "label": QtWidgets.QLabel("Table Name:"),
            "line": QtWidgets.QLineEdit(),
            "nameChk": QtWidgets.QCheckBox("Show Long Name"),
            "selectorA": views.SelectorWidget(side=views.SIDE_A),
            "selectorB": views.SelectorWidget(side=views.SIDE_B),
            "comparer": views.ComparingTable(),
            "statusLine": widgets.StatusLineWidget(main_logger, self),
        }

        layout = QtWidgets.QHBoxLayout(panel["top"])
        layout.addWidget(widget["label"])
        layout.addWidget(widget["line"])
        layout.addWidget(widget["nameChk"])

        layout = QtWidgets.QHBoxLayout(panel["control"])
        layout.addWidget(widget["selectorA"])
        layout.addWidget(widget["selectorB"])

        layout = QtWidgets.QVBoxLayout(panel["table"])
        layout.addWidget(widget["comparer"])
        layout.addWidget(widget["statusLine"])

        layout = QtWidgets.QVBoxLayout(panel["body"])
        layout.addWidget(panel["top"])
        layout.addSpacing(-14)
        layout.addWidget(panel["control"])
        layout.addSpacing(-24)
        layout.addWidget(panel["table"], stretch=True)
        layout.setContentsMargins(0, 0, 0, 0)

        tab = self.page["tab"]

        # Add Tab
        name = "New %d" % tab.count()
        index = tab.addTab(panel["body"], name)
        tab.setCurrentIndex(index)
        widget["line"].setText(name)

        # Connect
        widget["selectorA"].connect_comparer(widget["comparer"])
        widget["selectorB"].connect_comparer(widget["comparer"])
        widget["nameChk"].stateChanged.connect(
            widget["comparer"].on_name_mode_changed)
        widget["line"].textChanged.connect(
            lambda text: tab.setTabText(index, text))


def register_host_profiler(method):
    from . import lib
    lib.profile_from_host = method


def register_host_selector(method):
    from . import lib
    lib.select_from_host = method


def show():
    """Display Main GUI"""
    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    with lib.application():
        window = Window(parent=None)
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window
