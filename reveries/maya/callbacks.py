
import os
import importlib
from maya import cmds, OpenMaya
from avalon import maya, api as avalon

from .. import utils
from .lib import set_scene_timeline
from .pipeline import (
    is_editable,
    unlock_edit,
    reset_edit_lock,
    lock_edit_on_open,
)
from .vendor import sticker

from . import PYMEL_MOCK_FLAG


def on_task_changed(_, *args):
    avalon.logger.info("Changing Task module..")

    utils.init_app_workdir()
    maya.pipeline._on_task_changed()

    if not cmds.file(query=True, sceneName=True):
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
    reset_edit_lock()
    set_scene_timeline()


def on_open(_):
    reset_edit_lock()
    lock_edit_on_open()
    sticker.reveal()  # Show custom icon


def on_save(_):
    avalon.logger.info("Running callback on save..")
    if not is_editable():
        avalon.logger.info("Unlocking nodes..")
        unlock_edit()


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
