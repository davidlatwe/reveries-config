
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

        panel = {
            "control": QtWidgets.QWidget(),
            "table": QtWidgets.QWidget(),
        }

        widget = {
            "originSelector": views.OriginSelector(),
            "contrastSelector": views.ContrastSelector(),
            "comparerTable": views.ComparerTable(),
            "statusLine": widgets.StatusLineWidget(main_logger, self),
        }

        layout = QtWidgets.QHBoxLayout(panel["control"])
        layout.addWidget(widget["originSelector"])
        layout.addWidget(widget["contrastSelector"])

        layout = QtWidgets.QVBoxLayout(panel["table"])
        layout.addWidget(widget["comparerTable"])
        layout.addWidget(widget["statusLine"])

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(panel["control"])
        layout.addWidget(panel["table"])

        # Connect

        widget["originSelector"].origin_picked.connect(
            widget["comparerTable"].on_origin_picked)
        widget["originSelector"].origin_picked.connect(
            widget["contrastSelector"].on_origin_picked)

        widget["contrastSelector"].version_changed.connect(
            widget["comparerTable"].on_version_changed)

        # Init

        self.resize(840, 520)


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
