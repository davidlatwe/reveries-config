import os
from pyblish import api as pyblish
from avalon import api as avalon

PACKAGE_DIR = os.path.dirname(__file__)
PLUGINS_DIR = os.path.join(os.path.dirname(PACKAGE_DIR), "plugins")

# Global plugin paths
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "global", "publish")
LOADER_PATH = os.path.join(PLUGINS_DIR, "global", "load")

PYBLISH_PATH = os.path.dirname(pyblish.__file__)
PYBLISH_DEFAULT = os.path.join(PYBLISH_PATH, "plugins")

CONTRACTOR_PATH = os.path.join(PLUGINS_DIR, "global", "contractor")


def install():
    print("Registering global plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOADER_PATH)
    # Remove pyblish-base default plugins
    pyblish.deregister_plugin_path(PYBLISH_DEFAULT)


def uninstall():
    print("Deregistering global plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOADER_PATH)
    # Restore pyblish-base default plugins
    pyblish.register_plugin_path(PYBLISH_DEFAULT)
