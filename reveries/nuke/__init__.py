import os
import sys
import logging
import nuke

from avalon import api as avalon
from pyblish import api as pyblish

from . import menu
from .. import PLUGINS_DIR


self = sys.modules[__name__]

log = logging.getLogger("reveries.nuke")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "nuke", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "nuke", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "nuke", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "nuke", "inventory")


def install():
    from . import callbacks, pipeline

    # install pipeline menu
    menu.install()
    # install pipeline plugins
    log.info("Registering Nuke plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    # install callbacks
    log.info("Installing callbacks ... ")
    avalon.on("taskChanged", callbacks.on_task_changed)
    nuke.callbacks.addOnScriptSave(callbacks.on_save)
    nuke.callbacks.addOnScriptLoad(callbacks.on_load)

    pipeline.eval_deferred(callbacks.on_task_changed)


def uninstall():
    from . import callbacks

    log.info("Deregistering Nuke plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    # remove callbacks
    log.info("Uninstalling callbacks ... ")
    nuke.callbacks.removeOnScriptSave(callbacks.on_save)
    nuke.callbacks.removeOnScriptLoad(callbacks.on_load)

    menu.uninstall()
