import os
from pyblish import api as pyblish

PACKAGE_DIR = os.path.dirname(__file__)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")

PYBLISH_PATH = os.path.dirname(pyblish.__file__)
PYBLISH_DEFAULT = os.path.join(PYBLISH_PATH, "plugins")


def install():
    print("Registering global plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    # Remove pyblish-base default plugins
    pyblish.deregister_plugin_path(PYBLISH_DEFAULT)


def uninstall():
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    # Restore pyblish-base default plugins
    pyblish.register_plugin_path(PYBLISH_DEFAULT)
