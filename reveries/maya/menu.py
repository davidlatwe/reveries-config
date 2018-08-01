import sys
import logging
from avalon import api
from avalon.vendor.Qt import QtCore
from maya import cmds

self = sys.modules[__name__]
self._menu = api.Session["AVALON_LABEL"] + "menu"

log = logging.getLogger(__name__)


def install():
    from . import interactive

    def deferred():
        # Append to Avalon's menu
        cmds.menuItem(divider=True)

        cmds.menuItem("Snap!", command=interactive.active_view_snapshot)

    # Allow time for uninstallation to finish.
    QtCore.QTimer.singleShot(200, deferred)


def uninstall():
    pass
