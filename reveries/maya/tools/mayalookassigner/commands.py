
import logging
import json
import os

import maya.cmds as cmds

from avalon import io, api
from avalon.maya.pipeline import AVALON_CONTAINER_ID
from avalon.vendor import six

from ....utils import get_representation_path_
from ....maya import lib
from ...pipeline import (
    AVALON_INTERFACE_ID,
    get_interface_from_container,
    parse_container,
)


log = logging.getLogger(__name__)


def get_workfile():
    path = cmds.file(query=True, sceneName=True) or "untitled"
    return os.path.basename(path)


def get_workfolder():
    return os.path.dirname(cmds.file(query=True, sceneName=True))


def select(nodes):
    cmds.select(nodes)


def get_interface_from_namespace(namespaces):
    """Return interface nodes from namespace

    Args:
        namespaces (str, unicode or set): Target subsets' namespaces

    Returns:
        list: List of interface node in long name

    """
    if isinstance(namespaces, six.string_types):
        namespaces = [namespaces]

    interfaces = list()

    for namespace in namespaces:
        interfaces += lib.lsAttrs({"id": AVALON_INTERFACE_ID,
                                   "namespace": ":" + namespace})

    return cmds.ls(cmds.sets(interfaces, query=True, nodesOnly=True),
                   long=True)


def list_descendents(nodes):
    """Include full descendant hierarchy of given nodes.

    This is a workaround to cmds.listRelatives(allDescendents=True) because
    this way correctly keeps children instance paths (see Maya documentation)

    This fixes LKD-26: assignments not working as expected on instanced shapes.

    Return:
        list: List of children descendents of nodes

    """
    result = []
    while True:
        nodes = cmds.listRelatives(nodes,
                                   fullPath=True)
        if nodes:
            result.extend(nodes)
        else:
            return result


def get_selected_nodes():
    """Get information from current selection"""

    selection = cmds.ls(selection=True, long=True)
    hierarchy = list_descendents(selection)
    nodes = list(set(selection + hierarchy))

    return nodes


def get_all_asset_nodes():
    """Get all assets from the scene, container based

    Returns:
        list: list of dictionaries
    """

    host = api.registered_host()

    nodes = []
    for container in host.ls():
        # We are not interested in looks but assets!
        if container["loader"] == "LookLoader":
            continue

        # Gather all information
        container_name = container["objectName"]
        nodes += cmds.sets(container_name, query=True, nodesOnly=True) or []

    return nodes


_cached_containerized_nodes = dict()
_interface = (lambda con: get_interface_from_container(con))
_asset_id = (lambda con: cmds.getAttr(_interface(con) + ".assetId"))


def get_asset_id_from_node(node):
    """Get asset id by lookup container that this node belongs to
    Args:
        node (str): node long name

    Returns:
        str
    """
    if node in _cached_containerized_nodes:
        return _cached_containerized_nodes[node]

    _cached_containerized_nodes.clear()

    containers = {
        container: set(cmds.ls(cmds.sets(container, query=True),
                               long=True))
        for container in lib.lsAttrs({"id": AVALON_CONTAINER_ID})
        if not cmds.getAttr(container + ".loader") == "LookLoader"
    }
    for container, content in containers.items():
        _id = _asset_id(container)
        for _node in content:
            if not lib.hasAttr(_node, lib.AVALON_ID_ATTR_LONG):
                continue
            _cached_containerized_nodes[_node] = _id

    return _cached_containerized_nodes.get(node)


def create_asset_id_hash(nodes):
    """Create a hash based on `AvalonID` attribute value
    Args:
        nodes (list): a list of nodes

    Returns:
        dict
    """
    node_id_hash = dict()
    for node in cmds.ls(nodes, long=True):
        if not lib.hasAttr(node, lib.AVALON_ID_ATTR_LONG):
            continue
        asset_id = get_asset_id_from_node(node)
        if asset_id is None:
            continue

        if asset_id not in node_id_hash:
            node_id_hash[asset_id] = list()
        node_id_hash[asset_id].append(node)

    return node_id_hash


def create_items_from_nodes(nodes):
    """Create an item for the view based the container and content of it

    It fetches the look document based on the asset ID found in the content.
    The item will contain all important information for the tool to work.

    If there is an asset ID which is not registered in the project's collection
    it will log a warning message.

    Args:
        nodes (list): list of maya nodes

    Returns:
        list of dicts

    """

    asset_view_items = []

    id_hashes = create_asset_id_hash(nodes)
    if not id_hashes:
        return asset_view_items

    for _id, id_nodes in id_hashes.items():
        asset = io.find_one({"_id": io.ObjectId(_id)},
                            projection={"name": True})

        # Skip if asset id is not found
        if not asset:
            log.warning("Id not found in the database, skipping '%s'." % _id)
            log.warning("Nodes: %s" % id_nodes)
            continue

        # Collect available look subsets for this asset
        looks = list_loaded_looks(asset["_id"])

        # Collect namespaces the asset is found in
        namespaces = set()
        for node in id_nodes:
            namespace = lib.get_ns(node)
            namespaces.add(namespace)

        asset_view_items.append({"label": asset["name"],
                                 "asset": asset,
                                 "looks": looks,
                                 "namespaces": namespaces})

    return asset_view_items


def list_loaded_looks(asset_id):
    """Return all look subsets in scene for the given asset
    """
    look_subsets = list()

    for container in lib.lsAttrs({"id": AVALON_CONTAINER_ID}):
        if (cmds.getAttr(container + ".loader") == "LookLoader" and
                _asset_id(container) == str(asset_id)):

            look = parse_container(container)

            version_id = io.ObjectId(look["versionId"])
            version = io.find_one({"_id": version_id},
                                  projection={"name": True})
            look["version"] = version["name"]

            look_subsets.append(look)

    return look_subsets


def remove_unused_looks():
    """Removes all loaded looks for which none of the shaders are used.

    This will cleanup all loaded "LookLoader" containers that are unused in
    the current scene.

    """

    host = api.registered_host()

    unused = list()
    for container in host.ls():
        if container["loader"] == "LookLoader":
            members = cmds.sets(container["objectName"], query=True)
            look_sets = cmds.ls(members, type="objectSet")
            for look_set in look_sets:
                # If the set is used than we consider this look *in use*
                if cmds.sets(look_set, query=True):
                    break
            else:
                unused.append(container)

    for container in unused:
        log.info("Removing unused look container: %s", container['objectName'])
        api.remove(container)

    log.info("Finished removing unused looks. (see log for details)")


def assign_look(namespaces, look):
    """Assign looks via namespaces

    Args:
        namespaces (str, unicode or set): Target subsets' namespaces
        look (dict): The container data of look

    """
    representation_id = io.ObjectId(look["representation"])
    representation = io.find_one({"_id": representation_id})

    parents = io.parenthood(representation)
    package_path = get_representation_path_(representation, parents)

    file_name = representation["data"]["linkFname"]
    relationship = os.path.join(package_path, file_name)

    if not os.path.isfile(relationship):
        log.warning("Look development asset "
                    "has no relationship data.\n"
                    "{!r} was not found".format(relationship))
        return

    # Load map
    with open(relationship) as f:
        relationships = json.load(f)

    namespace = look["namespace"][1:]

    # Apply shader to target subset by namespace
    if isinstance(namespaces, six.string_types):
        namespaces = [namespaces]
    target_namespaces = [ns + ":" for ns in namespaces]

    lib.apply_shaders(relationships["shaderById"],
                      namespace,
                      target_namespaces)
