
from avalon.vendor.Qt import QtWidgets, QtGui, QtCore


class LineHTMLDelegate(QtWidgets.QStyledItemDelegate):
    """
    https://stackoverflow.com/a/5443112/4145300
    """

    def __init__(self, parent=None):
        super(LineHTMLDelegate, self).__init__(parent)

        view = self.parent()
        proxy = view.model()
        model = proxy.sourceModel()

        self.proxy = proxy
        self.style = view.style()
        self.role = model.HTMLTextRole

    def paint(self, painter, option, index):

        index = self.proxy.mapToSource(index)
        text = index.data(self.role)

        doc = QtGui.QTextDocument()
        doc.setHtml(text)
        doc_layout = doc.documentLayout()

        self.style.drawControl(QtWidgets.QStyle.CE_ItemViewItem,
                               option,
                               painter)

        rect = option.rect
        rect.setTop(rect.top() + 5)

        painter.save()
        painter.translate(rect.topLeft())
        painter.setClipRect(rect.translated(-rect.topLeft()))

        ctx = doc_layout.PaintContext()
        doc_layout.draw(painter, ctx)

        painter.restore()

    # Read-only plain text

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        editor.setReadOnly(True)

        return editor

    def setEditorData(self, editor, index):
        value = index.data(QtCore.Qt.DisplayRole)
        editor.setText(value)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class NameEditDelegate(QtWidgets.QStyledItemDelegate):

    name_changed = QtCore.Signal()

    def displayText(self, value, locale):
        return value

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)

        def commit_data():
            self.commitData.emit(editor)  # Update model data
            self.name_changed.emit()   # Display model data
        editor.editingFinished.connect(commit_data)

        return editor

    def setEditorData(self, editor, index):
        value = index.data(QtCore.Qt.DisplayRole)
        editor.setText(value)

    def setModelData(self, editor, model, index):
        name = editor.text()
        model.setData(index, name)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class ResolutionEditor(QtWidgets.QWidget):

    value_changed = QtCore.Signal(list)

    def __init__(self, parent=None):
        super(ResolutionEditor, self).__init__(parent)

        weditor = QtWidgets.QLineEdit()
        heditor = QtWidgets.QLineEdit()

        weditor.setValidator(QtGui.QIntValidator())
        heditor.setValidator(QtGui.QIntValidator())

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(weditor)
        layout.addWidget(heditor)
        # This is important to make those QLineEdit widgets to have
        # proper hight in column.
        layout.setContentsMargins(2, 0, 2, 0)

        weditor.editingFinished.connect(self.on_editingFinished)
        heditor.editingFinished.connect(self.on_editingFinished)

        self.data = {
            "w": weditor,
            "h": heditor,
        }

    def on_editingFinished(self):
        self.value_changed.emit(self.get_value())

    def get_value(self):
        return (int(self.data["w"].text() or 0),
                int(self.data["h"].text() or 0))

    def set_value(self, value):
        w, h = value
        self.data["w"].setText(str(w))
        self.data["h"].setText(str(h))


class ResolutionDelegate(QtWidgets.QStyledItemDelegate):

    value_changed = QtCore.Signal(list)

    def displayText(self, value, locale):
        return "{} x {}".format(*value)

    def createEditor(self, parent, option, index):
        editor = ResolutionEditor(parent)

        def commit_data(value):
            self.commitData.emit(editor)  # Update model data
            self.value_changed.emit(value)
        editor.value_changed.connect(commit_data)

        return editor

    def setEditorData(self, editor, index):
        value = index.data(QtCore.Qt.DisplayRole)
        editor.set_value(value)

    def setModelData(self, editor, model, index):
        value = editor.get_value()
        model.setData(index, value)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
