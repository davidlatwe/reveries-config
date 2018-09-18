
import os
import importlib
from maya import cmds, OpenMaya
from avalon import maya, api as avalon

from .. import utils
from .lib import (
    set_avalon_uuid,
    set_scene_timeline,
)

from . import PYMEL_MOCK_FLAG


def on_task_changed(_, *args):
    avalon.logger.info("Changing Task module..")

    utils.init_app_workdir()
    maya.pipeline._on_task_changed()

    set_scene_timeline()


def on_init(_):
    if os.path.isfile(PYMEL_MOCK_FLAG):
        avalon.logger.info("Mocking PyMel..")
        importlib.import_module("reveries.maya.vendor.pymel_mock")

    avalon.logger.info("Running callback on init..")
    cmds.loadPlugin("AbcImport", quiet=True)
    cmds.loadPlugin("AbcExport", quiet=True)
    cmds.loadPlugin("fbxmaya", quiet=True)


def on_new(_):
    set_scene_timeline()


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
        set_avalon_uuid(node)


def before_save(return_code, _):
    """Prevent accidental overwrite of locked scene"""

    # Manually override message given by default dialog
    # Tested with Maya 2013-2017
    dialog_id = "s_TfileIOStrings.rFileOpCancelledByUser"
    message = ("Scene is locked, please save under a new name.")
    cmds.displayString(dialog_id, replace=True, value=message)

    # Returning false in C++ causes this to abort a save in-progress,
    # but that doesn't translate from Python. Instead, the `setBool`
    # is used to mimic this beahvior.
    # Docs: http://download.autodesk.com/us/maya/2011help/api/
    # class_m_scene_message.html#a6bf4288015fa7dab2d2074c3a49f936
    OpenMaya.MScriptUtil.setBool(return_code, not maya.is_locked())
