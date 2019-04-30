
import os
import sys
from avalon import api, lib, io


class FrameRangeSetterAction(api.Action):
    """Only project admin can access
    """
    name = "framerangesetter"
    label = "Frame Range"
    icon = "scissors"
    color = "#FA9576"
    order = 999     # at the end

    def is_compatible(self, session):
        required = ["AVALON_PROJECTS",
                    "AVALON_PROJECT",
                    "AVALON_SILO"]
        missing = [x for x in required
                   if session.get(x) in (None, "placeholder")]

        return not missing

    def process(self, session, **kwargs):
        env = os.environ.copy()
        env.update(session)
        return lib.launch(executable="python",
                          environment=env,
                          args=[__file__])


if __name__ == "__main__":

    from avalon import style, Session
    from avalon.vendor.Qt import QtWidgets, QtCore
    from reveries import utils

    class FrameRangeSetter(QtWidgets.QDialog):

        MAX = 9999

        def __init__(self, parent=None):
            super(FrameRangeSetter, self).__init__(parent)

            self.setWindowTitle("Set Frame Range")
            self.setFocusPolicy(QtCore.Qt.StrongFocus)
            self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)

            asset_menu = QtWidgets.QComboBox()
            asset_grp = self.make_group(asset_menu, "Asset Name")

            start_box = QtWidgets.QSpinBox()
            start_grp = self.make_group(start_box, "Start Frame")

            end_box = QtWidgets.QSpinBox()
            end_grp = self.make_group(end_box, "End Frame")

            handle_box = QtWidgets.QSpinBox()
            handle_grp = self.make_group(handle_box, "Handles")

            save_btn = QtWidgets.QPushButton("Save")

            body = QtWidgets.QVBoxLayout(self)
            body.addLayout(asset_grp)
            body.addLayout(start_grp)
            body.addLayout(end_grp)
            body.addLayout(handle_grp)
            body.addWidget(save_btn)

            asset_menu.currentIndexChanged.connect(self.on_asset_changed)
            start_box.valueChanged.connect(self.on_value_changed)
            end_box.valueChanged.connect(self.on_value_changed)
            handle_box.valueChanged.connect(self.on_value_changed)
            save_btn.clicked.connect(self.save_range)

            self.assets = asset_menu
            self.start = start_box
            self.end = end_box
            self.handles = handle_box

            project = io.find_one({"type": "project"})
            self.handles_min = project["data"]["handles"]
            self.end.setMaximum(self.MAX)

            self.find_assets()

        def make_group(self, widget, label):
            group = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel(label)
            group.addWidget(label)
            group.addWidget(widget)
            return group

        def min_handles(self, handles):
            return handles if handles < self.handles_min else self.handles_min

        def on_asset_changed(self):
            asset = self.assets.currentText()
            start, end, handles, _ = utils.get_timeline_data(asset_name=asset)

            self.end.setValue(end)
            self.start.setValue(start)
            self.handles.setValue(handles)

        def on_value_changed(self):
            start = self.start.value()
            end = self.end.value()
            handles = self.handles.value()

            self.start.setMaximum(end - 1)
            self.start.setMinimum(handles)

            self.end.setMaximum(self.MAX)
            self.end.setMinimum(start + 1)

            self.handles.setMaximum(start)
            self.handles.setMinimum(self.min_handles(handles))

        def find_assets(self):
            for asset in io.find({"silo": Session["AVALON_SILO"]},
                                 {"name": True},
                                 sort=[("name", 1)]):
                self.assets.addItem(asset["name"])

        def save_range(self):
            asset = self.assets.currentText()
            update = {
                "data.edit_in": self.start.value(),
                "data.edit_out": self.end.value(),
                "data.handles": self.handles.value(),
            }
            io.update_many({"type": "asset", "name": asset},
                           update={"$set": update})

    io.install()

    app = QtWidgets.QApplication(sys.argv)
    dialog = FrameRangeSetter()
    dialog.setStyleSheet(style.load_stylesheet())
    dialog.show()
    sys.exit(app.exec_())
