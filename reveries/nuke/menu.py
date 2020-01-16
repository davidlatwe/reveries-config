
from avalon import api
import pyblish.api
import pyblish_qml.api
import logging
import nuke

log = logging.getLogger("reveries.nuke")

PYBLISH_ICON = "pyblish.png"


def _publish_via_targets(targets):
    pyblish.api.deregister_all_targets()
    for target in targets:
        pyblish.api.register_target(target)
    pyblish_qml.api.show(targets=targets)


def find_index(menu, name):
    finder = (i for i, m in enumerate(menu.items())
              if m.name() == name)
    return next(finder, None)


def install():

    def publish_in_local(*args):
        _publish_via_targets(["default", "localhost"])

    def publish_in_deadline(*args):
        _publish_via_targets(["default", "deadline"])

    menubar = nuke.menu("Nuke")
    menu = menubar.findItem(api.Session["AVALON_LABEL"])

    publish = "Publish..."
    index = find_index(menu, publish)
    menu.removeItem(publish)
    menu.addCommand(publish,
                    publish_in_local,
                    index=index,
                    icon=PYBLISH_ICON)

    menu.addSeparator()
    menu.addCommand("Deadline Publish...",
                    publish_in_deadline,
                    icon=PYBLISH_ICON)


def uninstall():
    pass
