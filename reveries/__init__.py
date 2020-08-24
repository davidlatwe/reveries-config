import os
import sys
from pyblish import api as pyblish
from avalon import api as avalon

from .version import version, version_info, __version__


self = sys.modules[__name__]
self.installed = None


PACKAGE_DIR = os.path.dirname(__file__)
PLUGINS_DIR = os.path.join(os.path.dirname(PACKAGE_DIR), "plugins")

# plugins only for developers
DEVELOPER_DIR = os.environ.get("AVALON_DEV_PLUGINS", "")

# Global plugin paths
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "global", "publish")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "global", "inventory")
LOADER_PATH = os.path.join(PLUGINS_DIR, "global", "load")
DEV_LOADER_PATH = os.path.join(DEVELOPER_DIR, "global", "load")

PYBLISH_PATH = os.path.dirname(pyblish.__file__)
PYBLISH_DEFAULT = os.path.join(PYBLISH_PATH, "plugins")

LAUNCHER_ACTION_PATH = os.path.join(PLUGINS_DIR, "global", "launcher")
DEV_LAUNCHER_ACTION_PATH = os.path.join(DEVELOPER_DIR, "global", "launcher")

REVERIES_ICONS = os.path.join("$REVERIES_PATH", "res", "icons")

os.environ["REVERIES_PATH"] = os.path.dirname(PACKAGE_DIR)

# Show project only if user has registered as member
os.environ["AVALON_LAUNCHER_USE_PROJECT_MEMBER"] = "true"

# Deadline command application path
avalon.Session["AVALON_DEADLINE_APP"] = os.getenv("AVALON_DEADLINE_APP", "")


__all__ = [
    "version",
    "version_info",
    "__version__",
]


def install():  # pragma: no cover
    from avalon import io

    print("Registering global plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)
    avalon.register_plugin_path(avalon.Loader, LOADER_PATH)
    avalon.register_plugin_path(avalon.Loader, DEV_LOADER_PATH)

    # Check usd pipeline
    project = io.find_one({"type": "project"})

    if project.get('usd_pipeline', False):
        avalon.register_plugin_path(
            avalon.Loader,
            os.path.join(PLUGINS_DIR, "usd", "global", "load")
        )

    # Remove pyblish-base default plugins
    pyblish.deregister_plugin_path(PYBLISH_DEFAULT)

    self.installed = True


def uninstall():  # pragma: no cover
    print("Deregistering global plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.InventoryAction, INVENTORY_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOADER_PATH)
    avalon.deregister_plugin_path(avalon.Loader, DEV_LOADER_PATH)
    # Restore pyblish-base default plugins
    pyblish.register_plugin_path(PYBLISH_DEFAULT)

    self.installed = False


def register_launcher_actions():
    from avalon import api
    from launcher.actions import ProjectManagerAction
    avalon.deregister_plugin(api.Action, ProjectManagerAction)
    avalon.register_plugin_path(api.Action, LAUNCHER_ACTION_PATH)
    avalon.register_plugin_path(api.Action, DEV_LAUNCHER_ACTION_PATH)
