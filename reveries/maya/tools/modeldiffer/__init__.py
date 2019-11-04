
import sys
import logging
from maya import cmds

from avalon import style
from avalon.tools import lib
from avalon.vendor.Qt import QtWidgets
from ....maya import utils, pipeline
from ....tools.modeldiffer import app


__all__ = [
    "show",
]


module = sys.modules[__name__]
module.window = None


main_logger = logging.getLogger("modeldiffer")


def show():
    """Display Main GUI"""
    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    # Get Maya main window
    top_level_widgets = QtWidgets.QApplication.topLevelWidgets()
    mainwindow = next(widget for widget in top_level_widgets
                      if widget.objectName() == "MayaWindow")

    # Register method for selecting models from scene
    app.register_host_profiler(profile_from_host)
    app.register_host_selector(select_from_host)

    with lib.application():
        window = app.Window(parent=mainwindow)
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window


_hasher = utils.MeshHasher()


def _hash(mesh):
    _hasher.clear()
    _hasher.set_mesh(mesh)
    _hasher.update_points()
    _hasher.update_uvmap()

    return _hasher.digest()


def profile_from_host(container=None):
    """
    Args:
        container (dict, optional): container object
    """
    if container:
        # From Avalon container node (with node name comparing)
        #
        # In this mode, we know where the hierarchy root is, so
        # we can compare with node names.
        #
        root = pipeline.get_group_from_container(container["objectName"])

        meshes = cmds.ls(cmds.sets(container["objectName"], query=True),
                         type="mesh",
                         noIntermediate=True,
                         long=True)
    else:
        # From selection (only compare with mesh hash values)
        #
        # In this mode, we can not be sure that the mesh long name is
        # comapreable, so the name will not be compared.
        #
        root = None

        meshes = cmds.listRelatives(cmds.ls(selection=True, long=True),
                                    shapes=True,
                                    noIntermediate=True,
                                    fullPath=True,
                                    type="mesh")

    if not meshes:
        main_logger.warning("No mesh selected..")
        return

    profile = dict()

    for mesh in meshes:
        transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]

        if root and transform.startswith(root):
            namespace = container["namespace"][1:] + ":"
            name = transform[len(root):].replace(namespace, "")
        else:
            name = transform

        data = {
            "avalonId": utils.get_id(transform),
            "fullPath": transform,
            "points": None,
            "uvmap": None,
        }
        data.update(_hash(mesh))

        profile[name] = data

    return profile


def select_from_host(nodes):
    cmds.select(nodes, noExpand=True)
