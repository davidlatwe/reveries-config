
import os
import importlib
from maya.api import OpenMaya as om  # API 2.0
from maya import cmds, OpenMaya
from avalon import maya, api as avalon

from .. import utils, plugins, lib
from .vendor import sticker

from . import PYMEL_MOCK_FLAG, utils as maya_utils, lib as maya_lib, pipeline


def _outliner_hide_set_member():
    """Set outliner default display options

    Turn off `showSetMembers` for avoiding long wait on a big objectSet that
    being accidentally selected.

    """
    options = {
        "showShapes": False,
        "showSetMembers": False,
        "showReferenceMembers": False,
        "showDagOnly": True,
    }
    avalon.logger.info("Disabling outliner set member display..")
    for outliner_pan in cmds.getPanel(type="outlinerPanel") or []:
        outliner = cmds.outlinerPanel(outliner_pan,
                                      query=True,
                                      outlinerEditor=True)
        # Set options
        cmds.outlinerEditor(outliner, edit=True, **options)


def _pop_sceneinventory():
    avalon.logger.warning("Scene has outdated content.")

    # Find maya main window
    parent = maya.pipeline.get_main_window()

    if parent is None:
        avalon.logger.info("Skipping outdated content pop-up "
                           "because Maya window can't be found.")
    else:
        # Show outdated pop-up
        respond = plugins.message_box_warning(
            title="Maya scene has outdated content",
            message="There are outdated subsets in your Maya scene.",
            optional=True
        )
        if respond:
            import avalon.tools.cbsceneinventory as tool
            tool.show(parent=parent)


def on_task_changed(_, *args):
    avalon.logger.info("Changing Task module..")

    utils.init_app_workdir()
    maya.pipeline._on_task_changed()

    if not cmds.file(query=True, sceneName=True):
        pipeline.set_scene_timeline()


def on_init(_):
    if os.path.isfile(PYMEL_MOCK_FLAG):
        avalon.logger.info("Mocking PyMel..")
        importlib.import_module("reveries.maya.vendor.pymel_mock")

    avalon.logger.info("Running callback on init..")
    cmds.loadPlugin("AbcImport", quiet=True)
    cmds.loadPlugin("AbcExport", quiet=True)
    cmds.loadPlugin("fbxmaya", quiet=True)

    avalon.logger.info("Installing callbacks on import..")

    OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kAfterImport,
        on_import
    )
    OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kBeforeImport,
        before_import
    )
    OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kAfterImportReference,
        on_import_reference
    )
    OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kBeforeImportReference,
        before_import_reference
    )

    avalon.logger.info("Installing callbacks on reference..")

    # API 2.0
    om.MSceneMessage.addCheckFileCallback(
        om.MSceneMessage.kBeforeCreateReferenceCheck,
        before_create_reference
    )
    cmds.evalDeferred("from reveries.maya import callbacks;"
                      "callbacks._outliner_hide_set_member()")

    avalon.logger.info("Installing callbacks before new..")

    OpenMaya.MSceneMessage.addCallback(
        OpenMaya.MSceneMessage.kBeforeNew,
        before_new
    )


def before_new(_):
    # We need to save current FPS here because after scene renewed, FPS will
    # be changed to Maya default FPS.
    pipeline._current_fps["_"] = maya_lib.current_fps()


def on_new(_):
    try:
        pipeline.set_scene_timeline()
    except Exception as e:
        cmds.warning(e.message)

    cmds.evalDeferred("from reveries.maya import callbacks;"
                      "callbacks._outliner_hide_set_member()")


def on_open(_):
    sticker.reveal()  # Show custom icon

    cmds.evalDeferred("from reveries.maya import callbacks;"
                      "callbacks._outliner_hide_set_member()")

    # (Medicine)
    #
    maya_utils.drop_interface()
    # Only fix containerized file nodes
    nodes = set()
    for container in maya.ls():
        nodes.update(cmds.ls(cmds.sets(container["objectName"], query=True),
                             type="file"))
    maya_utils.fix_texture_file_nodes(list(nodes))

    if cmds.about(batch=True):
        # For log reading and debug
        print("Maya API version: %s" % cmds.about(api=True))
        if cmds.pluginInfo("mtoa", q=True, loaded=True):
            version = cmds.pluginInfo("mtoa", q=True, version=True)
            print("MtoA version: %s" % version)
    else:
        if lib.any_outdated():
            _pop_sceneinventory()


def on_save(_):
    avalon.logger.info("Running callback on save..")


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

    avalon.logger.info("Cleaning up unused plugins..")
    maya_utils.remove_unused_plugins()
    maya_utils.kill_turtle()


_nodes = {"_": None}


def before_import(_):
    avalon.logger.info("Running callback before import..")
    # Collect all nodes in scene
    _nodes["_"] = set(cmds.ls())


def on_import(_):
    avalon.logger.info("Running callback on import..")

    before_nodes = _nodes["_"]
    after_nodes = set(cmds.ls())

    imported_nodes = list(after_nodes - before_nodes)
    maya_utils.update_id_verifiers(imported_nodes)
    _nodes["_"] = None

    sticker.reveal()  # Show custom icon


def before_import_reference(_):
    avalon.logger.info("Running callback before import reference..")
    # Collect all referenced nodes in scene
    _nodes["_"] = set(cmds.ls(referencedNodes=True))


def on_import_reference(_):
    avalon.logger.info("Running callback on import reference..")

    before_nodes = _nodes["_"]
    after_nodes = set(cmds.ls(referencedNodes=True))

    imported_nodes = list(before_nodes - after_nodes)
    maya_utils.update_id_verifiers(imported_nodes)
    _nodes["_"] = None


def before_create_reference(reference_node,
                            referenced_file,
                            clientData=None):
    """Using API 2.0"""
    avalon.logger.info("Running callback before create reference..")

    # (Medicine) Patch bad env var embedded path.
    bug = "$AVALON_PROJECTS$AVALON_PROJECT"
    fix = "$AVALON_PROJECTS/$AVALON_PROJECT"
    path = reference_node.rawFullName()
    if path.startswith(bug):
        path = path.replace(bug, fix)
        reference_node.setRawFullName(path)

    return True


_event_callbacks = {}


def register_event_callback(token, event, func, data=None):
    # API 2.0
    callback_id = om.MEventMessage.addEventCallback(event, func, data)
    _event_callbacks[token] = callback_id


def deregister_event_callback(token):
    callback_id = _event_callbacks.pop(token, None)
    if callback_id:
        om.MMessage.removeCallback(callback_id)


def deregister_all_event_callbacks():
    om.MMessage.removeCallbacks(list(_event_callbacks.values()))
    _event_callbacks.clear()
