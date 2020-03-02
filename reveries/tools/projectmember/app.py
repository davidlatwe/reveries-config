
import sys
import getpass

from avalon import io, style
from avalon.tools import lib as tools_lib
from avalon.vendor import qtawesome
from avalon.vendor.Qt import QtWidgets, QtCore


module = sys.modules[__name__]
module.window = None


class Window(QtWidgets.QWidget):

    _user = getpass.getuser().lower()

    def __init__(self, parent=None):
        super(Window, self).__init__(parent=parent)

        self.setWindowIcon(qtawesome.icon("fa.users", color="#F0F3F4"))
        self.setWindowTitle("Project Member")
        self.setWindowFlags(QtCore.Qt.Window)

        widget = {
            "refresh": QtWidgets.QPushButton(),
            "projects": QtWidgets.QComboBox(),
            "btnAdd": QtWidgets.QPushButton(),
            "btnDel": QtWidgets.QPushButton(),
        }

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(widget["refresh"])
        layout.addWidget(widget["projects"], stretch=True)
        layout.addWidget(widget["btnAdd"])
        layout.addWidget(widget["btnDel"])

        widget["refresh"].setIcon(qtawesome.icon("fa.refresh",
                                                 color="#E5E7E9"))
        widget["btnAdd"].setIcon(qtawesome.icon("fa.user-plus",
                                                color="#58D68D"))
        widget["btnDel"].setIcon(qtawesome.icon("fa.user-times",
                                                color="#A93226"))

        widget["projects"].currentTextChanged.connect(self.on_text_changed)
        widget["refresh"].clicked.connect(self.on_refresh_clicked)
        widget["btnAdd"].clicked.connect(self.on_add_clicked)
        widget["btnDel"].clicked.connect(self.on_del_clicked)

        self.widget = widget
        self.init_projects()
        self.resize(480, 40)

    def init_projects(self):
        self._projects = {
            project["name"]: project
            for project in io.projects()
            if project["data"].get("visible", True)  # Discard hidden projects
        }
        self.widget["projects"].addItems(sorted(self._projects.keys()))

    def on_text_changed(self, text):
        self.widget["btnAdd"].setEnabled(False)
        self.widget["btnDel"].setEnabled(False)

        def on_changed():
            project = self._projects[text]
            member = project["data"].get("role", {}).get("member", [])
            if self._user in member:
                self.widget["btnDel"].setEnabled(True)
            else:
                self.widget["btnAdd"].setEnabled(True)

        tools_lib.schedule(on_changed, 400, channel="projectmember")

    def on_refresh_clicked(self):
        self.widget["projects"].clear()
        self.init_projects()

    def on_add_clicked(self):
        name = self.widget["projects"].currentText()

        col = self._get_project_collection(name)
        col.update_one({"type": "project"},
                       {"$addToSet": {"data.role.member": self._user}})

        self._update_project_data(name)

        self.widget["btnAdd"].setEnabled(False)
        self.widget["btnDel"].setEnabled(True)

    def on_del_clicked(self):
        name = self.widget["projects"].currentText()

        col = self._get_project_collection(name)
        col.update_one({"type": "project"},
                       {"$pull": {"data.role.member": self._user}})

        self._update_project_data(name)

        self.widget["btnAdd"].setEnabled(True)
        self.widget["btnDel"].setEnabled(False)

    @io.auto_reconnect
    def _update_project_data(self, name):
        col = self._get_project_collection(name)
        project = col.find_one({"type": "project"})
        self._projects[name] = project
        return project

    @io.auto_reconnect
    def _get_project_collection(self, name):
        return io._database[name]


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
