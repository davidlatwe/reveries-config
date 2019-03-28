
import logging
import json
import os

import maya.cmds as cmds

from avalon import io, api
from avalon.maya.pipeline import AVALON_CONTAINER_ID
from avalon.vendor import six

from ....utils import get_representation_path_
from ....maya import lib, utils
from ...pipeline import (
    AVALON_INTERFACE_ID,
    get_interface_from_container,
    get_container_from_namespace,
    parse_container,
)


log = logging.getLogger(__name__)


def get_workfile():
    path = cmds.file(query=True, sceneName=True) or "untitled"
    return os.path.basename(path)


def get_workfolder():
    return os.path.dirname(cmds.file(query=True, sceneName=True))


def select(nodes):
    cmds.select(nodes, noExpand=True)


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
                                   "namespace": namespace})

    return cmds.ls(cmds.sets(interfaces, query=True, nodesOnly=True),
                   type="transform",
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
        looks = list_looks(asset["_id"])

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


def list_looks(asset_id):
    """Return all look subsets from database for the given asset
    """
    look_subsets = list(io.find({"parent": io.ObjectId(asset_id),
                                 "type": "subset",
                                 "name": {"$regex": "look*"}}))
    for look in look_subsets:
        # Get the latest version of this look subset
        version = io.find_one({"type": "version",
                               "parent": look["_id"]},
                              sort=[("name", -1)])
        look["version"] = version["name"]
        look["versionId"] = version["_id"]

    return look_subsets


def load_look(look):
    """Load look subset if it's not been loaded
    """
    representation = io.find_one({"type": "representation",
                                  "parent": look["versionId"],
                                  "name": "LookDev"})
    representation_id = str(representation["_id"])

    for container in lib.lsAttrs({"id": AVALON_CONTAINER_ID,
                                  "loader": "LookLoader",
                                  "representation": representation_id}):
        log.info("Reusing loaded look ..")
        return parse_container(container)

    # Not loaded
    log.info("Using look for the first time ..")

    loaders = api.loaders_from_representation(api.discover(api.Loader),
                                              representation_id)
    Loader = next((i for i in loaders if i.__name__ == "LookLoader"), None)
    if Loader is None:
        raise RuntimeError("Could not find LookLoader, this is a bug")

    container = api.load(Loader, representation)
    return container


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


def get_relationship(look):
    representation_id = io.ObjectId(look["representation"])
    representation = io.find_one({"_id": representation_id})

    parents = io.parenthood(representation)
    package_path = get_representation_path_(representation, parents)

    file_name = representation["data"]["linkFname"]
    relationship = os.path.join(package_path, file_name)

    return relationship


def assign_look(namespaces, look, via_uv):
    """Assign looks via namespaces

    Args:
        namespaces (str, unicode or set): Target subsets' namespaces
        look (dict): The container data of look

    """
    relationship = get_relationship(look)

    if not os.path.isfile(relationship):
        log.warning("Look development asset "
                    "has no relationship data.\n"
                    "{!r} was not found".format(relationship))
        return

    # Load map
    with open(relationship) as f:
        relationships = json.load(f)

    # Apply shader to target subset by namespace
    if isinstance(namespaces, six.string_types):
        namespaces = [namespaces]
    target_namespaces = [ns + ":" for ns in namespaces]

    if via_uv:
        _look_via_uv(look, relationships, target_namespaces)
    else:
        _apply_shaders(look,
                       relationships["shaderById"],
                       target_namespaces)
        _apply_crease_edges(look,
                            relationships["creaseSets"],
                            target_namespaces)
        _apply_smooth_sets(look,
                           relationships.get("alSmoothSets"),
                           target_namespaces)


def _apply_shaders(look, relationship, target_namespaces):
    namespace = look["namespace"][1:]

    lib.apply_shaders(relationship,
                      namespace,
                      target_namespaces)


def _apply_crease_edges(look, relationship, target_namespaces):
    namespace = look["namespace"][1:]

    crease_sets = lib.apply_crease_edges(relationship,
                                         namespace,
                                         target_namespaces)
    cmds.sets(crease_sets, forceElement=look["objectName"])


def _apply_smooth_sets(look, relationship, target_namespaces):
    namespace = look["namespace"][1:]

    if relationship is not None:
        try:
            from ....maya import arnold
        except RuntimeError:
            pass
        else:
            arnold.utils.apply_smooth_sets(
                relationship,
                namespace,
                target_namespaces
            )


def _look_via_uv(look, relationships, target_namespaces):
    """Assign looks via namespaces and using UV hash as hint

    In some cases, a setdress liked subset may assembled from a numbers of
    duplicated models, and for some reason the duplicated models may be given
    different Avalon UUIDs. Which cause the look only able to apply to one of
    those models.

    By the help of UV hash, as long as there's one set of model's Avalon UUID
    is correct, the rest of the models can compare with thier UV hashes and
    use that as a hint to apply look.

    """

    hasher = utils.MeshHasher()
    uv_via_id = dict()
    id_via_uv = dict()
    for target_namespace in target_namespaces:
        for mesh in cmds.ls(target_namespace + "*",
                            type="mesh",  # We can only hash meshes.
                            long=True):
            node = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]

            id = utils.get_id(node)
            if id in uv_via_id:
                continue

            hasher.clear()
            hasher.set_mesh(node)
            hasher.update_uvmap()
            uv_hash = hasher.digest()["uvmap"]
            uv_via_id[id] = uv_hash

            if uv_hash not in id_via_uv:
                id_via_uv[uv_hash] = set()
            id_via_uv[uv_hash].add(id)

    # Apply shaders
    #
    shader_by_id = dict()
    for shader, ids in relationships["shaderById"].items():
        shader_by_id[shader] = list()

        for id_ in ids:
            id, faces = (id_.rsplit(".", 1) + [""])[:2]

            uv_hash = uv_via_id[id]
            same_uv_ids = id_via_uv[uv_hash]
            shader_by_id[shader] += [".".join([i, faces]) for i in same_uv_ids]

    _apply_shaders(look, shader_by_id, target_namespaces)

    # Apply crease edges
    #
    crease_by_id = dict()
    for level, members in relationships["creaseSets"].items():
        crease_by_id[level] = list()

        for member in members:
            id, edges = member.split(".")

            uv_hash = uv_via_id[id]
            same_uv_ids = id_via_uv[uv_hash]
            crease_by_id[level] += [".".join([i, edges]) for i in same_uv_ids]

    _apply_crease_edges(look, crease_by_id, target_namespaces)

    # Apply Arnold smooth sets
    #
    if relationships.get("alSmoothSets") is None:
        return

    smooth_by_id = dict()
    for id, attrs in relationships["alSmoothSets"].items():
        uv_hash = uv_via_id[id]
        same_uv_ids = id_via_uv[uv_hash]
        for i in same_uv_ids:
            smooth_by_id[i] = attrs

    _apply_smooth_sets(look, smooth_by_id, target_namespaces)


def remove_look(namespaces, asset_ids):

    look_sets = set()
    for container in lib.lsAttrs({"id": AVALON_CONTAINER_ID,
                                  "loader": "LookLoader"}):
        container = parse_container(container)
        if container["assetId"] not in asset_ids:
            continue

        members = cmds.sets(container["objectName"], query=True)
        look_sets.update(cmds.ls(members, type="objectSet"))

    shaded = list()
    for namespace in namespaces:
        container = get_container_from_namespace(namespace)
        nodes = cmds.sets(container, query=True)
        shaded += cmds.ls(nodes, type=("transform", "surfaceShape"))

    for look_set in look_sets:
        for member in cmds.sets(look_set, query=True) or []:
            if member.rsplit(".")[0] in shaded:
                cmds.sets(member, remove=look_set)

    # Assign to lambert1
    cmds.sets(shaded, forceElement="initialShadingGroup")
