from avalon.vendor.Qt import QtWidgets
from avalon import style


class MessageBoxWindow(QtWidgets.QMessageBox):
    def __init__(self, parent=None, msg_type=None, window_title=None,
                 text=None, info_text=None, detail_text=None):
        super(MessageBoxWindow, self).__init__(parent=parent)

        self.setStyleSheet(style.load_stylesheet())

        msg_type = msg_type or QtWidgets.QMessageBox.Information
        window_title = window_title or "MessageBox"
        text = text or "This is a message box"
        info_text = info_text
        detail_text = detail_text

        self.setIcon(msg_type)

        self.setText(text)
        self.setWindowTitle(window_title)

        if info_text:
            self.setInformativeText(info_text)

        if detail_text:
            self.setDetailedText(detail_text)

        self.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

    def resizeEvent(self, event):
        result = super(MessageBoxWindow, self).resizeEvent(event)

        details_box = self.findChild(QtWidgets.QTextEdit)
        if details_box is not None:
            details_box.setFixedSize(details_box.sizeHint())

        return result
