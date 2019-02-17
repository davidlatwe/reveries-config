import os
import sys
from pyblish import api as pyblish
from avalon import api as avalon

from .version import version, version_info, __version__


self = sys.modules[__name__]
self.installed = None


PACKAGE_DIR = os.path.dirname(__file__)
PLUGINS_DIR = os.path.join(os.path.dirname(PACKAGE_DIR), "plugins")

# Global plugin paths
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "global", "publish")
LOADER_PATH = os.path.join(PLUGINS_DIR, "global", "load")

PYBLISH_PATH = os.path.dirname(pyblish.__file__)
PYBLISH_DEFAULT = os.path.join(PYBLISH_PATH, "plugins")

CONTRACTOR_PATH = os.path.join(PLUGINS_DIR, "global", "contractor")
LAUNCHER_ACTION_PATH = os.path.join(PLUGINS_DIR, "global", "launcher")

REVERIES_ICONS = os.path.join("$REVERIES_PATH", "res", "icons")

os.environ["REVERIES_PATH"] = os.path.dirname(PACKAGE_DIR)

__all__ = [
    "version",
    "version_info",
    "__version__",
]


def install():  # pragma: no cover
    print("Registering global plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOADER_PATH)
    # Remove pyblish-base default plugins
    pyblish.deregister_plugin_path(PYBLISH_DEFAULT)

    self.installed = True


def uninstall():  # pragma: no cover
    print("Deregistering global plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOADER_PATH)
    # Restore pyblish-base default plugins
    pyblish.register_plugin_path(PYBLISH_DEFAULT)

    self.installed = False


def register_launcher_actions():
    from avalon import api
    from launcher.actions import ProjectManagerAction
    avalon.deregister_plugin(api.Action, ProjectManagerAction)
    avalon.register_plugin_path(avalon.Action, LAUNCHER_ACTION_PATH)
