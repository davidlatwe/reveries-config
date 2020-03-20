
import os
import sys
import logging
import avalon.api
import avalon.io
from pyblish import api as pyblish

from .. import PLUGINS_DIR


self = sys.modules[__name__]
self.installed = None

log = logging.getLogger("reveries.filesys")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "filesys", "publish")


class Filesys(avalon.api.Action):

    name = "filesys"
    label = "File System"
    icon = None
    color = None
    order = 0

    config = {
        "schema": "avalon-core:application-1.0",

        "application_dir": "filesys",
        "executable": "python",
        "default_dirs": [
            "dumps",
        ]
    }


def install():
    app = Filesys()
    app.process(avalon.api.Session.copy(), launch=False)

    avalon.io.install()

    pyblish.api.register_host("python")
    pyblish.api.register_host("filesys")

    # install pipeline plugins
    pyblish.register_plugin_path(PUBLISH_PATH)

    self.installed = True


def uninstall():
    avalon.io.uninstall()

    pyblish.api.deregister_host("python")
    pyblish.api.deregister_host("filesys")

    # uninstall pipeline plugins
    pyblish.deregister_plugin_path(PUBLISH_PATH)

    self.installed = False
