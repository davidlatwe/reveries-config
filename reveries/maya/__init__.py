import os
import logging

import avalon.maya.commands as commands
import avalon.api as avalon

from pyblish import api as pyblish
from maya import mel

from .. import PLUGINS_DIR
from . import menu, callbacks
from .lib import set_scene_timeline


log = logging.getLogger("reveries.maya")

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
    avalon.on("taskChanged", callbacks.on_task_changed)
    avalon.on("init", callbacks.on_init)
    avalon.on("new", callbacks.on_new)
    avalon.on("save", callbacks.on_save)
    avalon.before("save", callbacks.before_save)

    # Temporarily workaround
    # script node: uiConfigurationScriptNode
    mel.eval("global proc CgAbBlastPanelOptChangeCallback(string $pass){}")
    log.info("Unknown proc <CgAbBlastPanelOptChangeCallback> "
             "workaround init.")

    # override avalon.maya menu function
    commands.reset_frame_range = set_scene_timeline


def uninstall():
    # uninstall pipeline menu
    menu.uninstall()
    # uninstall pipeline plugins
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)
