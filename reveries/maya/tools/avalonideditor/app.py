
import sys

from avalon import style
from avalon.tools import lib
from avalon.vendor.Qt import QtWidgets, QtCore
from avalon.vendor import qtawesome

from . import view


module = sys.modules[__name__]
module.window = None


class Window(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(Window, self).__init__(parent=parent)

        self.setWindowIcon(qtawesome.icon("fa.list", color="#DFDFDF"))
        self.setWindowTitle("Avalon Id Editor")
        self.setWindowFlags(QtCore.Qt.Window)

        selection_outline = view.SelectionOutline()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(selection_outline)

        self.data = {
            "selectionOutline": selection_outline
        }
        selection_outline.start()

        self.resize(840, 360)

    def closeEvent(self, event):
        self.data["selectionOutline"].stop()
        return super(Window, self).closeEvent(event)


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
