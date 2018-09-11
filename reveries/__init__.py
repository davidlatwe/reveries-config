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
