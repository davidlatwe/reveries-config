import sys
import logging
from avalon import api
from avalon.vendor.Qt import QtCore
from maya import cmds

from . import PYMEL_MOCK_FLAG

self = sys.modules[__name__]
self._menu = api.Session.get("AVALON_LABEL", "Avalon") + "menu"

log = logging.getLogger(__name__)


def install():
    from . import interactive

    def deferred():
        # Append to Avalon's menu
        cmds.menuItem(divider=True)

        cmds.menuItem("Snap!", command=interactive.active_view_snapshot)

        cmds.menuItem("LookDev",
                      label="LookDev",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

#        cmds.menuItem("V-Ray Attributes", command="""
# import reveries.maya.tools
# reveries.maya.tools.show('vray_attrs_setter')
# """)
        cmds.menuItem("Look Assigner", parent="LookDev", command="""
import reveries.maya.tools
reveries.maya.tools.show('mayalookassigner')
""")

        cmds.menuItem("Swap Modle", parent="LookDev",
                      command=interactive.swap_to_published_model)

        # System
        cmds.menuItem("Load PyMel", parent="System", command="""
import sys, os
MOCK_FLAG = {!r}
if os.path.isfile(MOCK_FLAG):
    os.remove(MOCK_FLAG)
if "pymel.core" in sys.modules:
    del sys.modules["pymel.core"]
import pymel.core
""".format(PYMEL_MOCK_FLAG))

        cmds.menuItem("Mock PyMel", parent="System", command="""
with open({!r}, "w") as flag:
    flag.write("")
""".format(PYMEL_MOCK_FLAG))

    # Allow time for uninstallation to finish.
    QtCore.QTimer.singleShot(200, deferred)


def uninstall():
    pass
