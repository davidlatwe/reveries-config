import os
import logging
import uuid

from maya import cmds, OpenMaya
from pyblish import api as pyblish
from avalon import maya, api as avalon
from . import menu


log = logging.getLogger("reveries.maya")

PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "maya", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "maya", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "maya", "create")


def install():
    # install pipeline menu
    menu.install()
    # install pipeline plugins
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)

    # install callbacks
    log.info("Installing callbacks ... ")
    avalon.on("taskChanged", on_task_changed)
    avalon.on("init", on_init)
    avalon.on("new", on_new)
    avalon.on("save", on_save)
    avalon.before("save", before_save)


def uninstall():
    # uninstall pipeline menu
    menu.uninstall()
    # uninstall pipeline plugins
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)


def _set_uuid(node):
    """Add avID ( Avalon ID ) to `node`
    Unless one already exists.
    """

    attr = "{0}.avID".format(node)

    if not cmds.objExists(attr):
        cmds.addAttr(node, shortName="avID",
                     longName="AvalonID", dataType="string")
        _, uid = str(uuid.uuid4()).rsplit("-", 1)
        cmds.setAttr(attr, uid, type="string")


def on_task_changed(_, *args):
    avalon.logger.info("Changing Task module..")


def on_init(_):
    pass


def on_new(_):
    pass


def on_save(_):
    """Automatically add IDs to new nodes
    Any transform of a mesh, without an exising ID,
    is given one automatically on file save.
    """

    avalon.logger.info("Running callback on save..")

    nodes = (set(cmds.ls(type="mesh", long=True)) -
             set(cmds.ls(long=True, readOnly=True)) -
             set(cmds.ls(long=True, lockedNodes=True)))

    transforms = cmds.listRelatives(list(nodes), parent=True) or list()

    # Add unique identifiers
    for node in transforms:
        _set_uuid(node)


def before_save(return_code, _):
    """Prevent accidental overwrite of locked scene"""

    # Manually override message given by default dialog
    # Tested with Maya 2013-2017
    dialog_id = "s_TfileIOStrings.rFileOpCancelledByUser"
    message = ("Scene is locked, please save under a new name "
               "or run cmds.remove(\"lock\") to override")
    cmds.displayString(dialog_id, replace=True, value=message)

    # Returning false in C++ causes this to abort a save in-progress,
    # but that doesn't translate from Python. Instead, the `setBool`
    # is used to mimic this beahvior.
    # Docs: http://download.autodesk.com/us/maya/2011help/api/
    # class_m_scene_message.html#a6bf4288015fa7dab2d2074c3a49f936
    OpenMaya.MScriptUtil.setBool(return_code, not maya.is_locked())
