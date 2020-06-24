
import os
import sys
import logging
import contextlib
import avalon.api
import pyblish.api

from .. import PLUGINS_DIR


self = sys.modules[__name__]
self.installed = None
self._data = dict()
self._instances = dict()

log = logging.getLogger("reveries.filesys")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "filesys", "publish")
CREATE_PATH = os.path.join(PLUGINS_DIR, "filesys", "create")


class Filesys(avalon.api.Application):

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

    app = Filesys()  # Init workdir
    app.process(avalon.api.Session.copy(), launch=False)

    pyblish.api.register_host("python")
    pyblish.api.register_host("filesys")

    # install pipeline plugins
    pyblish.api.register_plugin_path(PUBLISH_PATH)
    avalon.api.register_plugin_path(avalon.api.Creator, CREATE_PATH)

    self.installed = True


def uninstall():

    pyblish.api.deregister_host("python")
    pyblish.api.deregister_host("filesys")

    # uninstall pipeline plugins
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Creator, CREATE_PATH)

    self.installed = False


def put_data(key, value):
    """Put data into workspace

    Args:
        key: Workspace data key
        value: Workspace data value

    Returns:
        None

    """
    self._data[key] = value


def has_data(key):
    """Is `key` exists in workspace data ?

    Args:
        key: Workspace data key

    Returns:
        (bool)

    """
    return key in self._data


def get_data(key, default=None):
    """Get workspace data with default

    Args:
        key: Workspace data key
        default (optional): default value if key not exists

    Returns:
        Workspace data value or `default`

    """
    return self._data.get(key, default)


def pop_data(key, default=None):
    """Pop workspace data with default

    Args:
        key: Workspace data key
        default (optional): default value if key not exists

    Returns:
        Workspace data value or `default`

    """
    return self._data.pop(key, default)


def put_instance(name, data):
    """Put instance data into workspace

    Args:
        name (str): Subset name
        data (dict): Data for creating instance

    Returns:
        None

    """
    self._instances[name] = data


def iter_instances():
    """Iterate workspace instances

    Yields:
        name (str): Subset name
        data (dict): Data for creating instance

    """
    for name, data in self._instances.items():
        yield name, data


def new():
    """Reset workspace data and instances"""
    self._data.clear()
    self._instances.clear()


def ls():
    return []


@contextlib.contextmanager
def maintained_selection():
    try:
        yield
    finally:
        pass
