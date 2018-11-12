import os
import sys
import logging

try:
    from maya import mel
except ImportError:
    raise ImportError("Module 'reveries.maya' require Autodesk Maya.")

import avalon.maya.commands as commands
import avalon.api as avalon

from pyblish import api as pyblish

from .. import PLUGINS_DIR
from ..utils import override_event
from .lib import set_scene_timeline


self = sys.modules[__name__]
self.installed = None

log = logging.getLogger("reveries.maya")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "maya", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "maya", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "maya", "create")

PYMEL_MOCK_FLAG = os.path.join(os.environ["MAYA_APP_DIR"], "pymel.mock")


def install():  # pragma: no cover
    from . import menu, callbacks

    # install pipeline menu
    menu.install()
    # install pipeline plugins
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)

    # install callbacks
    log.info("Installing callbacks ... ")
    avalon.on("init", callbacks.on_init)
    avalon.on("new", callbacks.on_new)
    avalon.on("save", callbacks.on_save)
    avalon.before("save", callbacks.before_save)

    log.info("Overriding existing event 'taskChanged'")
    override_event("taskChanged", callbacks.on_task_changed)

    # Temporarily workaround
    # script node: uiConfigurationScriptNode
    mel.eval("global proc CgAbBlastPanelOptChangeCallback(string $pass){}")
    log.info("Unknown proc <CgAbBlastPanelOptChangeCallback> "
             "workaround init.")

    # override avalon.maya menu function
    commands.reset_frame_range = set_scene_timeline

    self.installed = True


def uninstall():  # pragma: no cover
    from . import menu

    # uninstall pipeline menu
    menu.uninstall()
    # uninstall pipeline plugins
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    self.installed = False


def collect_container_metadata(container):
    """Collect container additional data

    This will be called by `host.ls()`, which will parse container data and
    the data collected from this method.

    Args:
        container (str): container node name

    Returns:
        dict: Additional key-value dataset

    """
    # TODO: Collect interface data
    return {}
