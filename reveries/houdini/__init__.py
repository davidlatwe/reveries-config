
import os
import logging

from pyblish import api as pyblish
import pyblish_qml.settings

from avalon import api as avalon

from . import callbacks
from .. import PLUGINS_DIR


log = logging.getLogger("reveries.houdini")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "houdini", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "houdini", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "houdini", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "houdini", "inventory")


def install():
    from avalon import io

    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    # Check USD pipeline
    project = io.find_one({"name": avalon.Session["AVALON_PROJECT"], "type": "project"})

    if project.get('usd_pipeline', False):
        # pyblish.register_plugin_path(os.path.join(PLUGINS_DIR, "usd", "houdini", "publish"))
        avalon.register_plugin_path(
            avalon.Loader,
            os.path.join(PLUGINS_DIR, "usd", "houdini", "load")
        )
        avalon.register_plugin_path(
            avalon.Creator,
            os.path.join(PLUGINS_DIR, "usd", "houdini", "create")
        )
        pyblish.register_plugin_path(
            os.path.join(PLUGINS_DIR, "usd", "houdini", "publish"))

    # install callbacks
    print("Installing callbacks ... ")
    avalon.before("save", callbacks.before_save)
    avalon.on("save", callbacks.on_save)
    avalon.on("open", callbacks.on_open)
    avalon.on("taskChanged", callbacks.on_task_changed)

    # Config Pyblish QML
    pyblish_qml.settings.Directions = {
        "Local Publish": {
            "awesomeIcon": "motorcycle",
            "description": "Publish from this computer",
            "targets": ["default", "localhost"],
        },
        "Deadline Publish": {
            "awesomeIcon": "rocket",
            "description": "Publish in Deadline render farm",
            "targets": ["default", "deadline"],
        },
    }
