from avalon.vendor.Qt import QtWidgets
from avalon.vendor.Qt import QtCore
from avalon.vendor.Qt import QtGui

from avalon.vendor import qtawesome
from avalon import style


class ValidateWidget(QtWidgets.QDialog):
    def __init__(self, parent=None, validate_data=None):
        """
        Validate widget.
        :param parent: Parent widget.
        :param validate_data: Validate data.
        validate_data = {
            'BillboardGroup': {
                'BillboardA': {
                    'status': True,
                    'status_log': '',
                    'geom_usd_file_path': r''
                },
                'BillboardB': {
                    'status': False,
                    'status_log': 'No Asset publish',
                    'geom_usd_file_path': r''
                },
                'BillboardC': {
                    'status': False,
                    'status_log': 'No USD model publish',
                    'geom_usd_file_path': r''
                }
            },
            'CanGroup': {
                'CanA': {
                    'status': False,
                    'status_log': 'No USD model publish',
                    'geom_usd_file_path': r''
                },
                'CanB': {
                    'status': True,
                    'status_log': '',
                    'geom_usd_file_path': r''
                }
            }
        }
        """
        super(ValidateWidget, self).__init__(parent=parent)

        self.validate_data = validate_data
        self.publish_data = {}
        self._init_ui()
        self.skip_pub = True

        self.tree.expandToDepth(1)
        self.tree.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        self.resize(450, 300)
        self.setStyleSheet(style.load_stylesheet())

    def _init_ui(self):
        self.setWindowIcon(qtawesome.icon("fa.group", color="#1590fb"))
        self.setWindowTitle('USD Set Group Validation')

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setDropIndicatorShown(True)

        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)  # Set items can be multi-selected
        self.tree.headerItem().setTextAlignment(0, QtCore.Qt.AlignCenter)
        self.tree.headerItem().setTextAlignment(1, QtCore.Qt.AlignCenter)

        self.tree.setHeaderLabels(['SubAsset Name', 'Validation Context'])

        index_color = 0
        for set_name, subset_info in self.validate_data.items():
            set_name_item = QtWidgets.QTreeWidgetItem()
            set_name_item.setText(0, set_name)
            set_name_item.setCheckState(0, QtCore.Qt.Checked)
            set_name_item.setTextAlignment(1, QtCore.Qt.AlignHCenter)

            index_color += 1
            self._set_item_background_color(index_color, set_name_item)

            self.tree.addTopLevelItem(set_name_item)

            # Check set status
            if not subset_info.get('status', True):
                _msg = subset_info.get('status_log', '')
                set_name_item.setForeground(0, QtGui.QBrush(QtGui.QColor(255, 255, 0)))
                set_name_item.setText(1, _msg)
                set_name_item.setCheckState(0, QtCore.Qt.Unchecked)

            for subset_name, validate_info in subset_info.items():
                if subset_name in ['status', 'status_log']:
                    continue

                child_item = QtWidgets.QTreeWidgetItem(set_name_item)
                child_item.setText(0, subset_name)

                index_color += 1
                self._set_item_background_color(index_color, child_item)

                if validate_info.get('status', False):
                    pass_label = self.validate_pass_label()
                    self.tree.setItemWidget(child_item, 1, pass_label)
                else:
                    _log = validate_info.get('status_log', 'Error')
                    child_item.setText(1, _log)
                    child_item.setForeground(0, QtGui.QBrush(QtGui.QColor(255, 0, 0)))
                    child_item.setTextAlignment(1, QtCore.Qt.AlignHCenter)

        # Continue publish button
        pub_button = QtWidgets.QPushButton("Continue Publish")
        pub_button.clicked.connect(self.find_checked)

        # Cancel button
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close_win)

        self.tree.itemChanged.connect(self.handleChanged)

        # Widget layout
        btn_lay = QtWidgets.QHBoxLayout()
        btn_lay.addWidget(pub_button)
        btn_lay.addWidget(cancel_btn)

        main_lay = QtWidgets.QVBoxLayout()
        main_lay.addWidget(self.tree)
        main_lay.addLayout(btn_lay)
        self.setLayout(main_lay)

    def close_win(self):
        self.skip_pub = True
        self.close()

    def _set_item_background_color(self, index_color, _item):
        if index_color % 2 == 0:
            _item.setBackground(0, QtGui.QColor('#383838'))
            _item.setBackground(1, QtGui.QColor('#383838'))

    def validate_pass_label(self):
        _label = QtWidgets.QLabel('')
        icon = qtawesome.icon("fa.check-square-o", color="green")  # "share-alt-square"  fa.sticky-note-o
        pixmap = icon.pixmap(18, 18)
        _label.setPixmap(pixmap)
        _label.setAlignment(QtCore.Qt.AlignCenter)
        _label.setStyleSheet("background: transparent;")

        return _label

    def get_pub_set(self):
        return list(self.publish_data.keys())

    def find_checked(self):
        checked = dict()
        root = self.tree.invisibleRootItem()
        signal_count = root.childCount()
        for i in range(signal_count):
            set_item = root.child(i)
            checked_sweeps = list()
            num_children = set_item.childCount()

            if set_item.checkState(0) == QtCore.Qt.Checked:
                for n in range(num_children):
                    child = set_item.child(n)
                    checked_sweeps.append(child.text(0))
                checked[set_item.text(0)] = checked_sweeps

        self.publish_data = checked
        self.skip_pub = False
        self.close()

    def handleChanged(self, item, column):
        # Get his status when the check status changes.
        if item.checkState(column) == QtCore.Qt.Checked:
            print("checked", item, item.text(column))
        if item.checkState(column) == QtCore.Qt.Unchecked:
            print("unchecked", item, item.text(column))

    def getText(self):
        # print self.tree

        # Get a selected item
        # print self.tree.currentItem().text(1) ;

        item_list = self.tree.selectedItems()
        for ii in item_list:
            print(ii.text(1))


class USDSetProgressBarWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(USDSetProgressBarWidget, self).__init__(parent=parent)

        self.progressbar = None
        self.validate_data = None
        self.validate_result = None
        self.setWindowTitle('Progress Bar')

        self._init_ui()
        self.setStyleSheet(style.load_stylesheet())

    def _init_ui(self):
        self.progressbar = QtWidgets.QProgressBar(self)
        self.progressbar.setGeometry(0, 0, 300, 25)
        self.progressbar.setMaximum(100)

        main_lay = QtWidgets.QVBoxLayout()
        main_lay.addWidget(self.progressbar)
        self.setLayout(main_lay)

    def setBarRange(self, min, max):
        self.progressbar.setRange(min, max)
