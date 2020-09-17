from avalon.vendor.Qt import QtWidgets


class MessageBoxWindow(QtWidgets.QMessageBox):
    def __init__(self, parent=None, msg_type=None, window_title=None,
                 text=None, info_text=None, detail_text=None):
        super(MessageBoxWindow, self).__init__(parent=parent)

        msg_type = msg_type or QtWidgets.QMessageBox.Information
        window_title = window_title or "MessageBox"
        text = text or "This is a message box"
        info_text = info_text or "This is additional information"
        detail_text = detail_text or "The details are as follows:"

        self.setIcon(msg_type)

        self.setText(text)
        self.setInformativeText(info_text)
        self.setWindowTitle(window_title)

        self.setDetailedText(detail_text)

        self.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

    def resizeEvent(self, event):
        result = super(MessageBoxWindow, self).resizeEvent(event)

        details_box = self.findChild(QtWidgets.QTextEdit)
        if details_box is not None:
            details_box.setFixedSize(details_box.sizeHint())

        return result
