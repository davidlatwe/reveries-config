
import avalon.api


class PrintRepresentation(avalon.api.InventoryAction):
    """Select container node"""

    label = "Print Representation"
    icon = "print"
    color = "#B5D2D7"
    order = 900

    @staticmethod
    def is_compatible(container):
        return True

    def process(self, containers):
        representations = set()
        for container in containers:
            representations.add(container["representation"])

        for id in representations:
            print(id)

        self.copy_id_to_clipboard("\n".join(representations))

    @staticmethod
    def copy_id_to_clipboard(path):
        from avalon.vendor.Qt import QtCore, QtWidgets

        app = QtWidgets.QApplication.instance()
        assert app, "Must have running QApplication instance"

        # Build mime data for clipboard
        mime = QtCore.QMimeData()
        mime.setText(path)
        mime.setUrls([QtCore.QUrl.fromLocalFile(path)])

        # Set to Clipboard
        clipboard = app.clipboard()
        clipboard.setMimeData(mime)
