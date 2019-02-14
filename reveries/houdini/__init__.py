
import os
import logging

from pyblish import api as pyblish

from avalon import api as avalon
from avalon.houdini import pipeline as houdini

from . import lib
from .. import PLUGINS_DIR


log = logging.getLogger("reveries.houdini")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "houdini", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "houdini", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "houdini", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "houdini", "inventory")


def install():

    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    # install callbacks
    log.info("Installing callbacks ... ")
    avalon.on("init", on_init)
    avalon.before("save", before_save)
    avalon.on("save", on_save)
    avalon.on("open", on_open)


def on_init(*args):
    houdini.on_houdini_initialize()


def before_save(*args):
    pass


def on_save(*args):

    avalon.logger.info("Running callback on save..")

    nodes = lib.get_id_required_nodes()
    for node, new_id in lib.generate_ids(nodes):
        lib.set_id(node, new_id, overwrite=False)


def on_open(*args):

    avalon.logger.info("Running callback on open..")
