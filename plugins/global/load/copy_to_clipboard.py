
import reveries.base as base


class CopyToClipboardLoader(base.PendableLoader):
    """Copy published file to clipboard to allow to paste the content"""
    representations = ["*"]
    families = ["*"]

    label = "Copy Path"
    order = 20
    icon = "clipboard"
    color = "#999999"

    def pendable_load(self, context, name=None, namespace=None, data=None):
        self.log.info("Added to clipboard: {0}".format(self.repr_dir))
        self.copy_path_to_clipboard(self.repr_dir)

    @staticmethod
    def copy_path_to_clipboard(path):
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
