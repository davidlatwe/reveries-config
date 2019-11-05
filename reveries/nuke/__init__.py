import os
import sys
import logging

import nuke

from avalon import api as avalon
from avalon.tools import workfiles
from pyblish import api as pyblish

from . import menu


self = sys.modules[__name__]
self.workfiles_launched = False

log = logging.getLogger("reveries.nuke")

PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "nuke", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "nuke", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "nuke", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "nuke", "inventory")


# registering pyblish gui regarding settings in presets
if os.getenv("PYBLISH_GUI", None):
    pyblish.register_gui(os.getenv("PYBLISH_GUI", None))


def install():
    ''' Installing all requarements for Nuke host
    '''

    log.info("Registering Nuke plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)

    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "write",
        "review"
    ]

    avalon.data["familiesStateDefault"] = False
    avalon.data["familiesStateToggled"] = family_states

    # Workfiles.
    launch_workfiles = os.environ.get("WORKFILES_STARTUP")

    if launch_workfiles:
        nuke.addOnCreate(launch_workfiles_app, nodeClass="Root")

    menu.install()


def launch_workfiles_app():
    '''Function letting start workfiles after start of host
    '''
    if not self.workfiles_launched:
        self.workfiles_launched = True
        workfiles.show(os.environ["AVALON_WORKDIR"])


def uninstall():
    '''Uninstalling host's integration
    '''
    log.info("Deregistering Nuke plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    pyblish.deregister_callback("instanceToggled", on_pyblish_instance_toggled)

    menu.uninstall()


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle node passthrough states on instance toggles."""

    log.info("instance toggle: {}, old_value: {}, new_value:{} ".format(
        instance, old_value, new_value))

    from avalon.nuke import (
        viewer_update_and_undo_stop,
        add_publish_knob
    )

    # Whether instances should be passthrough based on new value

    with viewer_update_and_undo_stop():
        n = instance[0]
        try:
            n["publish"].value()
        except ValueError:
            n = add_publish_knob(n)
            log.info(" `Publish` knob was added to write node..")

        n["publish"].setValue(new_value)
