
import os
import logging
import avalon.maya
import avalon.io

from collections import defaultdict
from avalon.maya.pipeline import (
    AVALON_CONTAINER_ID,
    AVALON_CONTAINERS,
    containerise,
)
from maya import cmds
from . import lib
from .vendor import sticker
from .capsule import namespaced, nodes_locker
from .. import REVERIES_ICONS, utils

AVALON_GROUP_ATTR = "subsetGroup"
AVALON_CONTAINER_ATTR = "container"


log = logging.getLogger(__name__)


_node_lock_state = {"_": None}


def is_editable():
    return _node_lock_state["_"] is None


def reset_edit_lock():
    _node_lock_state["_"] = None


def lock_edit():
    """Restrict scene modifications

    All nodes will be locked, except:
        * default nodes
        * startup cameras
        * renderLayerManager

    """
    all_nodes = set(cmds.ls(objectsOnly=True, long=True))
    defaults = set(cmds.ls(defaultNodes=True))
    cameras = set(lib.ls_startup_cameras())
    materials = set(cmds.ls(materials=True))

    nodes_to_lock = list((all_nodes - defaults - cameras).union(materials))
    nodes_to_lock.remove("renderLayerManager")

    # Save current lock state
    _node_lock_state["_"] = lib.acquire_lock_state(nodes_to_lock)
    # Lock
    lib.lock_nodes(nodes_to_lock)


def unlock_edit():
    """Unleash scene modifications

    Restore all nodes' previous lock states

    """
    lib.restore_lock_state(_node_lock_state["_"])
    reset_edit_lock()


def env_embedded_path(path):
    """Embed environment var `$AVALON_PROJECTS` and `$AVALON_PROJECT` into path

    This will ensure reference or cache path resolvable when project root
    moves to other place.

    """
    path = path.replace(
        avalon.api.registered_root(), "$AVALON_PROJECTS", 1
    )
    path = path.replace(
        avalon.Session["AVALON_PROJECT"], "$AVALON_PROJECT", 1
    )

    return path


def subset_group_name(namespace, name):
    return "{}:{}".format(namespace, name)


def container_naming(namespace, name, suffix):
    return "%s_%s_%s" % (namespace, name, suffix)


def unique_root_namespace(asset_name, family_name, parent_namespace=""):
    unique = avalon.maya.lib.unique_namespace(
        asset_name + "_" + family_name + "_",
        prefix=parent_namespace + ("_" if asset_name[0].isdigit() else ""),
        suffix="_",
    )
    return ":" + unique  # Ensure in root


def get_container_from_namespace(namespace):
    """Return container node from namespace

    Raise `RuntimeError` if getting none or more then one container.

    Arguments:
        namespace (str): Namespace string

    Returns a str

    """
    nodes = lib.lsAttrs({"id": AVALON_CONTAINER_ID}, namespace=namespace)

    if "*" in namespace:
        return nodes

    if not len(nodes) == 1:
        raise RuntimeError("Has none or more then one container, "
                           "this is a bug.")
    return nodes[0]


def get_container_from_group(group):
    """Return container node from subset group

    If the `group` is not a subset group node, return `None`.

    Args:
        group (str): Subset group node name

    Return:
        str or None

    """
    if not cmds.objExists(group):
        return None

    nodes = list()

    for node in cmds.listConnections(group + ".message",
                                     destination=True,
                                     source=False,
                                     type="objectSet") or []:
        if not cmds.objExists(node + ".id"):
            continue

        if cmds.getAttr(node + ".id") == AVALON_CONTAINER_ID:
            nodes.append(node)

    assert len(nodes) == 1, ("Group node has non or more then one container, "
                             "this is a bug.")
    return nodes[0]


def get_group_from_container(container):
    """Get top group node name from container node

    Arguments:
        container (str): Name of container node

    """
    try:
        group = cmds.listConnections(container + ".subsetGroup",
                                     source=True,
                                     destination=False,
                                     plugs=False)

        return cmds.ls(group, long=True)[0]

    except ValueError:
        # The subset of family 'look' does not have subsetGroup.
        return None


def apply_namespace_wrapper(namespace, nodes):
    """Put nodes into a namespace wrapper objectSet

    For nodes that could not or did not have namespace, by putting them
    into a special objectSet so those nodes can be found by the tools
    which require namespace to work with.

    That special objectSet node is the actual member of the namespace,
    and it's AvalonID value must be `lib.AVALON_NAMESPACE_WRAPPER_ID`.

    Those tools must use `.lib.ls_nodes_by_id` to find nodes, that's the
    function has the implementation of reading nodes inside the wrapper.

    (NOTE): Nodes that already has namespace will be ignored.

    Example use case:
        Currently used by XGen Legacy type subsets, since XGen Legacy did
        not fully namespace supported.

    Args:
        namespace (str): Namespace string that will apply to the wrapper
        nodes (list): A list of nodes that need to be wrapped

    Returns:
        (list): A list of wrapper nodes

    """
    from .utils import get_id_namespace, id_namespace, upsert_id

    id_cache = dict()
    wrapper_group = defaultdict(list)

    for node in nodes:
        # Ignore nodes that already has namespace
        if lib.get_ns(node) != ":":
            continue

        asset_id = get_id_namespace(node)
        if asset_id is None:
            continue

        if asset_id not in id_cache:
            id_cache[asset_id] = avalon.io.find_one(
                {"_id": avalon.io.ObjectId(asset_id)},
                projection={"name": True})["name"]

        asset_name = id_cache[asset_id]

        wrapper = namespace + ":wrapper_" + asset_name
        wrapper_group[(wrapper, asset_id)].append(node)

    wrappers = list()
    for (wrapper, asset_id), nodes in wrapper_group.items():
        if not cmds.objExists(wrapper):
            cmds.createNode("objectSet", name=wrapper)
            with id_namespace(asset_id):
                upsert_id(wrapper, id=lib.AVALON_NAMESPACE_WRAPPER_ID)

        cmds.sets(nodes, forceElement=wrapper)
        wrappers.append(wrapper)

    return wrappers


def container_metadata(container):
    """Get additional data from container node

    Arguments:
        container (str): Name of container node

    Returns:
        (dict)

    """
    return {}


def parse_container(container):
    """Parse data from container node with additional data

    Arguments:
        container (str): Name of container node

    Returns:
        data (dict)

    """
    data = avalon.maya.pipeline.parse_container(container)
    data.update(container_metadata(container))
    return data


def update_container(container, asset, subset, version, representation):
    """Update container node attributes' value and namespace

    Arguments:
        container (dict): container document
        asset (dict): asset document
        subset (dict): subset document
        version (dict): version document
        representation (dict): representation document

    """
    log.info("Updating container...")

    container_node = container["objectName"]

    namespace = container["namespace"]

    asset_changed = container["assetId"] != str(asset["_id"])
    version_changed = container["versionId"] != str(version["_id"])
    family_changed = False
    if version_changed:
        origin_version = avalon.io.find_one(
            {"_id": avalon.io.ObjectId(container["versionId"])})
        origin_family = origin_version["data"]["families"][0]
        new_family = version["data"]["families"][0]
        family_changed = origin_family != new_family

    if (asset_changed or family_changed):
        # Update namespace
        parent_namespace = namespace.rsplit(":", 1)[0] + ":"
        with namespaced(parent_namespace, new=False) as parent_namespace:
            parent_namespace = parent_namespace[1:]
            asset_name = asset["data"].get("shortName", asset["name"])
            family_name = version["data"]["families"][0].split(".")[-1]
            new_namespace = unique_root_namespace(asset_name,
                                                  family_name,
                                                  parent_namespace)
            cmds.namespace(parent=":" + parent_namespace,
                           rename=(namespace.rsplit(":", 1)[-1],
                                   new_namespace[1:].rsplit(":", 1)[-1]))

        namespace = new_namespace

    # Update data
    for key, value in {
        "name": subset["name"],
        "namespace": namespace,
        "assetId": str(asset["_id"]),
        "subsetId": str(subset["_id"]),
        "versionId": str(version["_id"]),
        "representation": str(representation["_id"]),
    }.items():
        cmds.setAttr(container_node + "." + key, value, type="string")

    name = subset["name"]

    # Rename group node
    group = container.get("subsetGroup")
    if group and cmds.objExists(group):
        cmds.rename(group, subset_group_name(namespace, name))

    # Rename container
    container_node = cmds.rename(
        container_node, container_naming(namespace, name, "CON"))

    # Rename reference node
    reference_node = next((n for n in cmds.sets(container_node, query=True)
                           if cmds.nodeType(n) == "reference"), None)
    if reference_node:
        with nodes_locker(reference_node, False, False, False):
            cmds.rename(reference_node, namespace + "RN")


def subset_containerising(name,
                          namespace,
                          container_id,
                          nodes,
                          context,
                          cls_name,
                          group_name):
    """Containerise loaded subset

    Containerizing imported/referenced nodes and connect subset group
    node's `message` attribute to container node.

    Arguments:
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        container_id (str): Container UUID
        nodes (list): Long names of imported/referenced nodes
        context (dict): Asset information
        cls_name (str): avalon Loader class name
        group_name (str): Top group node of imported/referenced new nodes

    """
    container = containerise(name=name,
                             namespace=namespace,
                             nodes=nodes,
                             context=context,
                             loader=cls_name)
    # Add additional data
    for key, value in {
        "containerId": container_id,
        "assetId": str(context["asset"]["_id"]),
        "subsetId": str(context["subset"]["_id"]),
        "versionId": str(context["version"]["_id"]),
    }.items():
        cmds.addAttr(container, longName=key, dataType="string")
        cmds.setAttr(container + "." + key, value, type="string")

    # Connect subset group
    if group_name and cmds.objExists(group_name):
        lib.connect_message(group_name, container, AVALON_GROUP_ATTR)

    # Put icon to main container
    main_container = cmds.ls(AVALON_CONTAINERS, type="objectSet")[0]
    _icon = os.path.join(REVERIES_ICONS, "container_main-01.png")
    sticker.put(main_container, _icon)

    # Apply icons
    container_icon = os.path.join(REVERIES_ICONS, "container-01.png")
    sticker.put(container, container_icon)

    if cmds.objExists(group_name):
        package_icon = os.path.join(REVERIES_ICONS, "package-01.png")
        sticker.put(group_name, package_icon)

    return parse_container(container)


def put_instance_icon(instance):
    instance_icon = os.path.join(REVERIES_ICONS, "instance-01.png")
    sticker.put(instance, instance_icon)
    return instance


def find_stray_textures(instance):
    """Find file nodes that were not containerized
    """
    stray = list()
    containers = lib.lsAttr("id", AVALON_CONTAINER_ID)

    for file_node in cmds.ls(instance, type="file"):
        sets = cmds.listSets(object=file_node) or []
        if any(s in containers for s in sets):
            continue

        stray.append(file_node)

    return stray


_uuid_required_node_types = {
    "reveries.model": {
        "transform",
    },
    "reveries.rig": {
        "transform",
    },
    "reveries.look": {
        "transform",
        "shadingDependNode",
        "THdependNode",
    },
    "reveries.setdress": {
        "transform",
    },
    "reveries.camera": {
        "transform",
        "camera",
    },
    "reveries.lightset": {
        "transform",
        "light",
        "locator",
    },
    "reveries.xgen": {
        "transform",
        # Listed from cmds.listNodeTypes("xgen/spline")
        # "xgmCurveToSpline",
        "xgmModifierClump",
        "xgmModifierCollision",
        "xgmModifierCut",
        "xgmModifierDisplacement",
        "xgmModifierGuide",
        "xgmModifierLinearWire",
        "xgmModifierNoise",
        "xgmModifierScale",
        "xgmModifierSculpt",
        "xgmSeExpr",
        "xgmSplineBase",
        "xgmSplineCache",
        "xgmSplineDescription",
        "xgmPalette",
        "xgmDescription",
    },
}


def uuid_required_node_types(family):
    try:
        types = _uuid_required_node_types[family]
    except KeyError:
        if family == "reveries.mayashare":
            types = set()
            for typ in _uuid_required_node_types.values():
                types.update(typ)
        else:
            raise

    return list(types)


def has_turntable():
    """Return turntable asset name if scene has loaded one

    Returns:
        str: turntable asset name, if scene has truntable asset loaded,
             else `None`

    """
    project = avalon.io.find_one({"type": "project"},
                                 {"data.pipeline.maya": True})
    turntable = project["data"]["pipeline"]["maya"].get("turntable")

    if turntable is None:
        return None

    if get_container_from_namespace(":{}_*".format(turntable)):
        return turntable


def set_scene_timeline(project=None, asset_name=None, strict=True):
    """Set timeline to correct frame range for the asset

    Args:
        project (dict, optional): Project document, query from database if
            not provided.
        asset_name (str, optional): Asset name, get from `avalon.Session` if
            not provided.
        strict (bool, optional): Whether or not to set the exactly frame range
            that pre-defined for asset, or leave the scene start/end untouched
            as long as the start/end frame could cover the pre-defined range.
            Default `True`.


    """
    log.info("Timeline setting...")

    start_frame, end_frame, fps = utils.compose_timeline_data(project,
                                                              asset_name)
    fps = lib.FPS_MAP.get(fps)

    if fps is None:
        raise ValueError("Unsupported FPS value: {}".format(fps))

    cmds.currentUnit(time=fps)

    if not strict:
        scene_start = cmds.playbackOptions(query=True, minTime=True)
        if start_frame < scene_start:
            cmds.playbackOptions(animationStartTime=start_frame)
            cmds.playbackOptions(minTime=start_frame)

        scene_end = cmds.playbackOptions(query=True, maxTime=True)
        if end_frame > scene_end:
            cmds.playbackOptions(animationEndTime=end_frame)
            cmds.playbackOptions(maxTime=end_frame)

    else:
        cmds.playbackOptions(animationStartTime=start_frame)
        cmds.playbackOptions(minTime=start_frame)
        cmds.playbackOptions(animationEndTime=end_frame)
        cmds.playbackOptions(maxTime=end_frame)

        cmds.currentTime(start_frame)


def set_resolution(project=None, asset_name=None):
    width, height = utils.get_resolution_data(project, asset_name)
    cmds.setAttr("defaultResolution.width", width)
    cmds.setAttr("defaultResolution.height", height)
