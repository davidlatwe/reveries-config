
import logging
import json
import os

import maya.cmds as cmds

from avalon import io, api
from avalon.maya.pipeline import AVALON_CONTAINER_ID

from ....utils import get_representation_path_
from ....maya import lib, utils
from ...pipeline import (
    get_container_from_namespace,
    get_group_from_container,
    parse_container,
)

from .models import UNDEFINED_SUBSET


log = logging.getLogger(__name__)


def get_workfile():
    path = cmds.file(query=True, sceneName=True) or "untitled"
    return os.path.basename(path)


def get_workfolder():
    return os.path.dirname(cmds.file(query=True, sceneName=True))


def select(nodes):
    cmds.select(nodes, noExpand=True)


def group_from_namespace(namespace):
    """Return group nodes from namespace

    Args:
        namespace (str, unicode): Target subset's namespace

    Returns:
        str: group node in long name

    """
    container = get_container_from_namespace(namespace)
    return get_group_from_container(container)


def get_asset_id(node):
    if not lib.hasAttr(node, lib.AVALON_ID_ATTR_LONG):
        return None
    return utils.get_id_namespace(node)


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


def get_selected_asset_nodes():

    host = api.registered_host()

    nodes = list()

    selection = cmds.ls(selection=True, long=True)
    hierarchy = list_descendents(selection)

    containers = list(host.ls())

    for node in set(selection + hierarchy):

        asset_id = get_asset_id(node)
        if asset_id is None:
            continue

        for container in containers:
            if cmds.sets(node, isMember=container["objectName"]):
                subset = container["name"]
                namespace = container["namespace"]
                break
        else:
            subset = UNDEFINED_SUBSET
            namespace = lib.get_ns(node)

        nodes.append({
            "node": node,
            "assetId": asset_id,
            "subset": subset,
            "namespace": namespace,
        })

    return nodes


def get_all_asset_nodes():
    """Get all assets from the scene, container based"""

    host = api.registered_host()

    nodes = list()

    for container in host.ls():
        # We only interested in surface assets !
        # (TODO): This black list should be somewhere else
        if container["loader"] in ("LookLoader",
                                   "CameraLoader",
                                   "LightSetLoader"):
            continue

        # Gather all information
        container_name = container["objectName"]
        subset = container["name"]
        namespace = container["namespace"]

        for node in cmds.ls(cmds.sets(container_name,
                                      query=True,
                                      nodesOnly=True),
                            long=True):

            asset_id = get_asset_id(node)
            if asset_id is None:
                continue

            nodes.append({
                "node": node,
                "assetId": asset_id,
                "subset": subset,
                "namespace": namespace,
            })

    return nodes


def create_items(nodes, selected_only=False):
    """Create an item for the view

    It fetches the look document based on the asset ID found in the content.
    The item will contain all important information for the tool to work.

    If there is an asset ID which is not registered in the project's collection
    it will log a warning message.

    Args:
        nodes (set): A set of maya nodes

    Returns:
        list of dicts

    """
    if not nodes:
        return []

    asset_view_items = []

    id_hashes = dict()
    for node in nodes:
        asset_id = node["assetId"]
        if asset_id not in id_hashes:
            id_hashes[asset_id] = list()
        id_hashes[asset_id].append(node)

    for asset_id, asset_nodes in id_hashes.items():
        asset = io.find_one({"_id": io.ObjectId(asset_id)},
                            projection={"name": True})

        # Skip if asset id is not found
        if not asset:
            log.warning("Asset id not found in the database, skipping '%s'."
                        % asset_id)
            continue

        # Collect available look subsets for this asset
        looks = list_looks(asset["_id"])
        loaded_looks = list_loaded_looks(asset["_id"])

        # Collect namespaces the asset is found in
        subsets = dict()
        namespace_nodes = dict()
        namespace_selection = dict()

        for node in asset_nodes:
            namespace = node["namespace"]
            subset = node["subset"]

            if namespace not in namespace_nodes:
                subsets[namespace] = subset
                namespace_nodes[namespace] = set()

            namespace_nodes[namespace].add(node["node"])

        namespaces = list(subsets.keys())

        if selected_only:
            namespace_selection = namespace_nodes
        else:
            for namespace in namespaces:
                selection = set()
                group = group_from_namespace(namespace)
                if group is not None:
                    selection.add(group)
                namespace_selection[namespace] = selection

        asset_view_items.append({"label": asset["name"],
                                 "asset": asset,
                                 "looks": looks,
                                 "loadedLooks": loaded_looks,
                                 "namespaces": namespaces,
                                 "subsets": subsets,
                                 "nodesByNamespace": namespace_nodes,
                                 "selectByNamespace": namespace_selection})

    return asset_view_items


def list_looks(asset_id):
    """Return all look subsets from database for the given asset
    """
    look_subsets = list(io.find({"parent": asset_id,
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


def list_loaded_looks(asset_id):
    look_subsets = list()
    cached_look = dict()

    for container in lib.lsAttrs({"id": AVALON_CONTAINER_ID,
                                  "loader": "LookLoader",
                                  "assetId": str(asset_id)}):

        subset_id = cmds.getAttr(container + ".subsetId")
        if subset_id in cached_look:
            look = cached_look[subset_id].copy()
        else:
            look = io.find_one({"_id": io.ObjectId(subset_id)})
            cached_look[subset_id] = look

        namespace = cmds.getAttr(container + ".namespace")
        # Example: ":Zombie_look_02_"
        look["No."] = namespace.split("_")[-2]  # result: "02"
        look["namespace"] = namespace

        look_subsets.append(look)

    return look_subsets


def load_look(look, overload=False):
    """Load look subset if it's not been loaded
    """
    representation = io.find_one({"type": "representation",
                                  "parent": look["versionId"],
                                  "name": "LookDev"})
    representation_id = str(representation["_id"])

    is_loaded = False
    for container in lib.lsAttrs({"id": AVALON_CONTAINER_ID,
                                  "loader": "LookLoader",
                                  "representation": representation_id}):
        if overload:
            is_loaded = True
            log.info("Overload look ..")
            break

        log.info("Reusing loaded look ..")
        return parse_container(container)

    if not is_loaded:
        # Not loaded
        log.info("Using look for the first time ..")

    loaders = api.loaders_from_representation(api.discover(api.Loader),
                                              representation_id)
    Loader = next((i for i in loaders if i.__name__ == "LookLoader"), None)
    if Loader is None:
        raise RuntimeError("Could not find LookLoader, this is a bug")

    container = api.load(Loader,
                         representation,
                         options={"overload": overload})
    return container


def get_loaded_look(look, *args, **kwargs):
    container = get_container_from_namespace(look["namespace"])
    return parse_container(container)


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

    # Gathering namespaces recursively
    #
    target_namespaces = set()

    for namespace in namespaces:
        target_namespaces.add(namespace)

        if namespace == ":":
            continue

        child_namespaces = cmds.namespaceInfo(namespace,
                                              listOnlyNamespaces=True,
                                              absoluteName=True,
                                              recurse=True) or []
        target_namespaces.update(child_namespaces)

    target_namespaces = list(ns + ":" for ns in target_namespaces)

    # Assign
    #
    if via_uv:
        _look_via_uv(look, relationships, target_namespaces)
    else:
        _apply_shaders(look,
                       relationships["shaderById"],
                       target_namespaces)
        _apply_crease_edges(look,
                            relationships["creaseSets"],
                            target_namespaces)

        arnold_attrs = relationships.get("arnoldAttrs",
                                         relationships.get("alSmoothSets"))
        _apply_ai_attrs(look,
                        arnold_attrs,
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


def _apply_ai_attrs(look, relationship, target_namespaces):
    namespace = look["namespace"][1:]

    if relationship is not None:
        try:
            from ....maya import arnold
        except RuntimeError:
            pass
        else:
            arnold.utils.apply_ai_attrs(
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
            uv_hash = hasher.digest().get("uvmap")

            if uv_hash is None:
                continue

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

            if id not in uv_via_id:
                # The id from relationships does not exists in scene
                continue

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

            if id not in uv_via_id:
                # The id from relationships does not exists in scene
                continue

            uv_hash = uv_via_id[id]
            same_uv_ids = id_via_uv[uv_hash]
            crease_by_id[level] += [".".join([i, edges]) for i in same_uv_ids]

    _apply_crease_edges(look, crease_by_id, target_namespaces)

    # Apply Arnold attributes
    #
    arnold_attrs = relationships.get("arnoldAttrs",
                                     relationships.get("alSmoothSets"))
    if arnold_attrs is None:
        return

    ai_attrs_by_id = dict()
    for id, attrs in arnold_attrs.items():

        if id not in uv_via_id:
            # The id from relationships does not exists in scene
            continue

        uv_hash = uv_via_id[id]
        same_uv_ids = id_via_uv[uv_hash]
        for i in same_uv_ids:
            ai_attrs_by_id[i] = attrs

    _apply_ai_attrs(look, ai_attrs_by_id, target_namespaces)


def remove_look(nodes, asset_ids):

    look_sets = set()
    for container in lib.lsAttrs({"id": AVALON_CONTAINER_ID,
                                  "loader": "LookLoader"}):
        container = parse_container(container)
        if container["assetId"] not in asset_ids:
            continue

        members = cmds.sets(container["objectName"], query=True)
        look_sets.update(cmds.ls(members, type="objectSet"))

    shaded = cmds.ls(nodes, type=("transform", "surfaceShape"))

    for look_set in look_sets:
        for member in cmds.sets(look_set, query=True) or []:
            if member.rsplit(".")[0] in shaded:
                cmds.sets(member, remove=look_set)

    # Assign to lambert1
    cmds.sets(shaded, forceElement="initialShadingGroup")
