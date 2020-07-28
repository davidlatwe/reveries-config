
import logging
from avalon.vendor.Qt import QtWidgets, QtCore, QtGui
from avalon.vendor import qtawesome
from avalon import tools


class _WidgetLogHandler(logging.Handler):

    def __init__(self, widget):
        super(_WidgetLogHandler, self).__init__()
        self.widget = widget

        format = "%(message)s"
        formatter = logging.Formatter(format)
        self.setFormatter(formatter)

    def emit(self, record):
        dotting = record.msg.endswith(".....")
        try:
            log = self.format(record)
            level = record.levelno
            self.widget.echo.emit(level, log, dotting)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)


class _LogLevelIconButton(QtWidgets.QPushButton):
    """Icon by log level"""

    def __init__(self, parent=None):
        super(_LogLevelIconButton, self).__init__(parent)

        self.level = logging.NOTSET
        self.previous = logging.NOTSET
        self.colors = {
            logging.NOTSET: "#404040",
            logging.DEBUG: "#976BBB",
            logging.INFO: "#6CA9C0",
            logging.WARNING: "#DBBC5A",
            logging.ERROR: "#F07B48",
            logging.CRITICAL: "#F33636",
        }
        self.icons = {
            level: qtawesome.icon("fa.bell", color=color).pixmap(16, 16)
            for level, color in self.colors.items()
        }

        self.setMinimumSize(18, 18)
        self.setMaximumSize(18, 18)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        color = QtGui.QColor(self.colors[self.previous])
        painter.setPen(color)
        painter.setBrush(QtGui.QBrush(color))
        painter.drawEllipse(0, 1, 4, 4)
        painter.drawPixmap(3, 0, self.icons[self.level])
        painter.end()


class StatusLineWidget(QtWidgets.QWidget):
    """Logging message receiver and displayer

    Args:
        logger: `logging.Logger` instance

    """

    echo = QtCore.Signal(int, str, int)

    def __init__(self, logger, parent=None):
        super(StatusLineWidget, self).__init__(parent)

        icon = _LogLevelIconButton()

        line = QtWidgets.QLineEdit()
        line.setReadOnly(True)
        line.setStyleSheet("""
            QLineEdit {
                border: 0px;
                border-radius: 6px;
                padding: 0 6px;
                color: #AAAAAA;
                background: #363636;
            }
        """)

        body = QtWidgets.QHBoxLayout(self)
        body.addWidget(icon)
        body.addWidget(line)

        handler = _WidgetLogHandler(self)
        logger.addHandler(handler)

        self.icon = icon
        self.line = line

        self.echo.connect(self.on_echo)
        self.icon.clicked.connect(lambda: self._echo(0, "", True))

    def _echo(self, level, log, reset=False):
        if reset:
            self.icon.previous = logging.NOTSET
        self.icon.level = level
        self.icon.update()
        self.line.setText(log)

    def on_echo(self, level, log, dotting=False):

        ALARM = logging.WARNING

        if level >= ALARM and level > self.icon.previous:
            self.icon.previous = level

        if dotting:
            # Display dotting animation
            if log.endswith("....."):
                log = log[:-4]
            else:
                log += "."

            self._echo(level, log)

            # Loop
            animator = (lambda: self.on_echo(level, log, dotting))
            tools.lib.schedule(animator, 300, channel="statusline")

        else:
            self._echo(level, log)

            if level < ALARM:
                # Back to default state
                job = (lambda: self._echo(0, ""))
            else:
                # Keep alarm
                job = (lambda: self._echo(level, log))

            tools.lib.schedule(job,
                               5000,
                               channel="statusline")


class Interrupter(QtWidgets.QProgressDialog):

    def __init__(self, title=None, label=None,
                 minimum=None, maximum=None, parent=None):
        super(Interrupter, self).__init__(parent=parent)

        if title:
            self.setWindowTitle(title)
        if label:
            self.setLabelText(label)
        if minimum:
            self.setMinimum(minimum)
        if maximum:
            self.setMaximum(maximum)
        self.setAutoClose(False)
        self.setAutoReset(True)
        self.setModal(True)

    def __enter__(self):
        self.show()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def is_canceled(self):
        return self.wasCanceled()

    def bump(self):
        current = self.value()
        self.setValue(current + 1)
