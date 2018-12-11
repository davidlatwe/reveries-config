
import os
import avalon.maya
import avalon.io

from avalon.maya.pipeline import (
    AVALON_CONTAINER_ID,
    AVALON_CONTAINERS,
    containerise,
)
from maya import cmds
from . import lib
from .vendor import sticker
from .capsule import namespaced, nodes_locker
from .. import REVERIES_ICONS


AVALON_PORTS = ":AVALON_PORTS"
AVALON_INTERFACE_ID = "pyblish.avalon.interface"

AVALON_GROUP_ATTR = "subsetGroup"
AVALON_CONTAINER_ATTR = "container"


def subset_group_name(namespace, name):
    return "{}:{}".format(namespace, name)


def container_naming(namespace, name, suffix):
    return "%s_%s_%s" % (namespace, name, suffix)


def unique_root_namespace(asset_name, parent_namespace=""):
    unique = avalon.maya.lib.unique_namespace(
        asset_name + "_",
        prefix=parent_namespace + ("_" if asset_name[0].isdigit() else ""),
        suffix="_",
    )
    return ":" + unique  # Ensure in root


def subset_interfacing(name,
                       namespace,
                       container_id,
                       nodes,
                       context,
                       suffix="PORT"):
    """Expose crucial `nodes` as an interface of a subset container

    Interfacing enables a faster way to access nodes of loaded subsets from
    outliner.

    Arguments:
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host interface
        container_id (str): Container UUID
        nodes (list): Long names of nodes for interfacing
        context (dict): Asset information
        suffix (str, optional): Suffix of interface, defaults to `_PORT`.

    Returns:
        interface (str): Name of interface assembly

    """
    from collections import OrderedDict
    from maya import cmds

    interface = cmds.sets(nodes,
                          name=container_naming(namespace, name, suffix))

    data = OrderedDict()
    data["id"] = AVALON_INTERFACE_ID
    data["namespace"] = namespace
    data["containerId"] = container_id
    data["assetId"] = str(context["asset"]["_id"])
    data["subsetId"] = str(context["subset"]["_id"])
    data["versionId"] = str(context["version"]["_id"])

    avalon.maya.lib.imprint(interface, data)

    main_interface = cmds.ls(AVALON_PORTS, type="objectSet")
    if not main_interface:
        main_interface = cmds.sets(empty=True, name=AVALON_PORTS)
        _icon = os.path.join(REVERIES_ICONS, "interface_main-01.png")
        sticker.put(main_interface, _icon)
    else:
        main_interface = main_interface[0]

    cmds.sets(interface, addElement=main_interface)

    return interface


def get_interface_from_container(container):
    """Return interface node from container

    Raise `RuntimeError` if getting none or more then one interface.

    Arguments:
        container (str): Name of container node

    Returns a str

    """
    namespace = cmds.getAttr(container + ".namespace")
    nodes = lib.lsAttrs({"id": AVALON_INTERFACE_ID}, namespace=namespace)

    if not len(nodes) == 1:
        raise RuntimeError("Container has none or more then one interface, "
                           "this is a bug.")
    return nodes[0]


def get_container_from_interface(interface):
    """Return container node from interface

    Raise `RuntimeError` if getting none or more then one container.

    Arguments:
        interface (str): Name of interface node

    Returns a str

    """
    namespace = cmds.getAttr(interface + ".namespace")
    nodes = lib.lsAttrs({"id": AVALON_CONTAINER_ID}, namespace=namespace)

    if not len(nodes) == 1:
        raise RuntimeError("Interface has none or more then one container, "
                           "this is a bug.")
    return nodes[0]


def get_group_from_container(container):
    """
    """
    transforms = cmds.ls(cmds.sets(container, query=True),
                         type="transform",
                         long=True)
    if not transforms:
        return None
    return sorted(transforms)[0]


def container_metadata(container):
    """
    """
    interface = get_interface_from_container(container)
    subset_group = get_group_from_container(container)
    container_id = cmds.getAttr(interface + ".containerId")
    asset_id = cmds.getAttr(interface + ".assetId")
    subset_id = cmds.getAttr(interface + ".subsetId")
    version_id = cmds.getAttr(interface + ".versionId")

    return {
        "interface": interface,
        "subsetGroup": subset_group,
        "containerId": container_id,
        "assetId": asset_id,
        "subsetId": subset_id,
        "versionId": version_id,
    }


def parse_container(container):
    """
    """
    data = avalon.maya.pipeline.parse_container(container)
    data.update(container_metadata(container))
    return data


def update_container(container, asset, subset, version, representation):
    """
    """
    container_node = container["objectName"]

    asset_changed = False
    subset_changed = False

    origin_asset = container["assetId"]
    update_asset = str(asset["_id"])

    namespace = container["namespace"]
    if not origin_asset == update_asset:
        asset_changed = True
        # Update namespace
        parent_namespace = namespace.rsplit(":", 1)[0] + ":"
        with namespaced(parent_namespace, new=False) as parent_namespace:
            parent_namespace = parent_namespace[1:]

            new_namespace = unique_root_namespace(update_asset,
                                                  parent_namespace)
            cmds.namespace(parent=":" + parent_namespace,
                           rename=(namespace.rsplit(":", 1)[-1],
                                   new_namespace[1:].rsplit(":", 1)[-1]))

        namespace = new_namespace
        # Update data
        cmds.setAttr(container_node + ".namespace", namespace, type="string")

    origin_subset = container["name"]
    update_subset = subset["name"]

    name = origin_subset
    if not origin_subset == update_subset:
        subset_changed = True
        name = subset["name"]
        # Rename group node
        group = container["subsetGroup"]
        cmds.rename(group, subset_group_name(namespace, name))
        # Update data
        cmds.setAttr(container_node + ".name", name, type="string")

    if any((asset_changed, subset_changed)):
        # Rename container
        container_node = cmds.rename(
            container_node, container_naming(namespace, name, "CON"))
        # Rename interface
        cmds.rename(container["interface"],
                    container_naming(namespace, name, "PORT"))
        # Rename reference node
        reference_node = next((n for n in cmds.sets(container_node, query=True)
                              if cmds.nodeType(n) == "reference"), None)
        if reference_node:
            # Unlock reference node
            with nodes_locker(reference_node, False, False, False):
                cmds.rename(reference_node, namespace + "RN")

    # Update representation id
    cmds.setAttr(container_node + ".representation",
                 str(representation["_id"]),
                 type="string")


def subset_containerising(name,
                          namespace,
                          container_id,
                          nodes,
                          ports,
                          context,
                          cls_name,
                          group_name):
    """Containerise loaded subset and build interface
    """
    interface = subset_interfacing(name=name,
                                   namespace=namespace,
                                   container_id=container_id,
                                   nodes=ports,
                                   context=context)
    container = containerise(name=name,
                             namespace=namespace,
                             nodes=nodes,
                             context=context,
                             loader=cls_name)
    # Put icon to main container
    main_container = cmds.ls(AVALON_CONTAINERS, type="objectSet")[0]
    _icon = os.path.join(REVERIES_ICONS, "container_main-01.png")
    sticker.put(main_container, _icon)

    # interface -> top_group.message
    #           -> container.message
    lib.connect_message(group_name, interface, AVALON_GROUP_ATTR)
    lib.connect_message(container, interface, AVALON_CONTAINER_ATTR)

    # Apply icons
    container_icon = os.path.join(REVERIES_ICONS, "container-01.png")
    interface_icon = os.path.join(REVERIES_ICONS, "interface-01.png")
    sticker.put(container, container_icon)
    sticker.put(interface, interface_icon)

    if cmds.objExists(group_name):
        package_icon = os.path.join(REVERIES_ICONS, "package-01.png")
        sticker.put(group_name, package_icon)

    return parse_container(container)
