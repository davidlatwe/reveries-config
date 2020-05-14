import sys
import logging
import maya.utils
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
        cmds.menuItem(divider=True, parent=self._menu)

        cmds.menuItem("Deadline Publish...",
                      command=publish_in_deadline,
                      image=tools.publish.ICON,
                      parent=self._menu)

        cmds.menuItem(divider=True, parent=self._menu)

        # Utilities
        cmds.menuItem("Menu_Utilities",
                      label="Utilities",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

        cmds.menuItem("Snap Shot", parent="Menu_Utilities",
                      command=interactive.active_view_snapshot)

        cmds.menuItem("Set Avalon Id", parent="Menu_Utilities",
                      command=interactive.apply_avalon_uuid)

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

        cmds.menuItem("FixRenderGlobalsEncoding",
                      label="Fix renderGlobalsEncoding",
                      parent="Menu_Render",
                      command=interactive.fix_renderGlobalsEncoding_not_found)

        # Modeling tools
        cmds.menuItem("Menu_Model",
                      label="Model",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

        cmds.menuItem("Avalon Id Editor", parent="Menu_Model", command="""
import reveries.maya.tools
reveries.maya.tools.show('avalonideditor')
""")
        cmds.menuItem("Model Differ", parent="Menu_Model", command="""
import reveries.maya.tools
reveries.maya.tools.show('modeldiffer')
""")
        cmds.menuItem("Combine With Id", parent="Menu_Model",
                      image="polyUnite.png",
                      command=interactive.combine_with_id)

        cmds.menuItem("Separate With Id", parent="Menu_Model",
                      image="polySeparate.png",
                      command=interactive.separate_with_id)

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

        # cmds.menuItem("Swap Modle", parent="Menu_LookDev",
        #               command=interactive.swap_to_published_model)

        # Rig tools
        cmds.menuItem("Menu_Rig",
                      label="Rig",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

        cmds.menuItem("Model Locker", parent="Menu_Rig", command="""
import reveries.maya.tools
reveries.maya.tools.show('modellocker')
""")
        cmds.menuItem("Transfer UV",
                      parent="Menu_Rig",
                      command=interactive.update_uv)

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

        cmds.menuItem("Menu_Sim",
                      label="Simulation",
                      tearOff=True,
                      subMenu=True,
                      parent=self._menu)

        cmds.menuItem("Pinner", parent="Menu_Sim", command="""
import reveries.maya.tools
reveries.maya.tools.show('pinner')
""")

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
    maya.utils.executeDeferred(
        lambda: QtCore.QTimer.singleShot(100, deferred)
    )


def uninstall():
    pass
