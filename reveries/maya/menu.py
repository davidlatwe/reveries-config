import sys
import logging
import pyblish.api
import pyblish_qml.api
from avalon import api, tools
from avalon.vendor.Qt import QtCore
from maya import cmds

from . import PYMEL_MOCK_FLAG

self = sys.modules[__name__]
self._menu = api.Session.get("AVALON_LABEL", "Avalon") + "menu"

log = logging.getLogger(__name__)


def _arnold_update_full_scene(*args):
    try:
        from . import arnold
    except RuntimeError:
        return

    arnold.utils.update_full_scene()


def _publish_via_targets(targets):
    pyblish.api.deregister_all_targets()
    for target in targets:
        pyblish.api.register_target(target)
    pyblish_qml.api.show(targets=targets)


def install():
    from . import interactive

    def publish_in_local(*args):
        _publish_via_targets(["default", "localhost"])

    def publish_in_deadline(*args):
        _publish_via_targets(["default", "deadline"])

    def deferred():
        cmds.menuItem("Publish___",  # Publish...
                      edit=True,
                      command=publish_in_local)

        # Append to Avalon's menu
        cmds.menuItem(divider=True)

        cmds.menuItem("Deadline Publish...",
                      command=publish_in_deadline,
                      image=tools.publish.ICON)

        cmds.menuItem(divider=True)

        cmds.menuItem("Snap!", command=interactive.active_view_snapshot)

        # Rendering tools
        cmds.menuItem("Menu_Render",
                      label="Render",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

        cmds.menuItem(divider=True, dividerLabel="Arnold")

        cmds.menuItem("ArnoldUpdateFullScene",
                      label="Update Full Scene",
                      parent="Menu_Render",
                      image="playbackLoopingContinuous.png",
                      command=_arnold_update_full_scene)

        # LookDev tools
        cmds.menuItem("Menu_LookDev",
                      label="LookDev",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

#        cmds.menuItem("V-Ray Attributes", command="""
# import reveries.maya.tools
# reveries.maya.tools.show('vray_attrs_setter')
# """)
        cmds.menuItem("Look Assigner", parent="Menu_LookDev", command="""
import reveries.maya.tools
reveries.maya.tools.show('mayalookassigner')
""")

        cmds.menuItem("Set AvalonUUID", parent="Menu_LookDev",
                      command=interactive.apply_avalon_uuid)

        cmds.menuItem("Swap Modle", parent="Menu_LookDev",
                      command=interactive.swap_to_published_model)

        # Rig tools
        cmds.menuItem("Menu_Rig",
                      label="Rig",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

        cmds.menuItem("Model Differ", parent="Menu_Rig", command="""
import reveries.maya.tools
reveries.maya.tools.show('modeldiffer')
""")

        # XGen tools
        cmds.menuItem("Menu_XGen",
                      label="XGen",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

        cmds.menuItem(divider=True, dividerLabel="XGen Legacy")

        cmds.menuItem("Bake All Descriptions",
                      parent="Menu_XGen",
                      command=interactive.bake_all_xgen_legacy_descriptions)
        cmds.menuItem("Bake All Modifiers",
                      parent="Menu_XGen",
                      command=interactive.bake_all_xgen_legacy_modifiers)
        cmds.menuItem("Copy Mesh To World",
                      parent="Menu_XGen",
                      command=interactive.copy_mesh_to_world)
        cmds.menuItem("Link Hair System",
                      parent="Menu_XGen",
                      command=interactive.link_palettes_to_hair_system)
        cmds.menuItem("Set RefWires Frame By Nucleus",
                      parent="Menu_XGen",
                      command=interactive.set_refwires_frame_by_nucleus)

        cmds.menuItem(divider=True, dividerLabel="XGen Interactive Groom")

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
