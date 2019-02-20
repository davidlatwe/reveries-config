
import os
import avalon.maya
import avalon.io

from avalon.maya.pipeline import (
    AVALON_CONTAINER_ID,
    AVALON_CONTAINERS,
    containerise,
    is_locked,
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


def lock_edit_on_open():
    publish_on_lock = [cmds.getAttr(node_attr)
                       for node_attr in cmds.ls("*.publishOnLock")]
    if is_locked() and any(publish_on_lock):
        lock_edit()


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


def subset_interfacing(name,
                       namespace,
                       container_id,
                       nodes,
                       context,
                       suffix="PORT"):
    """Expose crucial `nodes` as an interface of a subset container

    Interfacing enables a faster way to access nodes of loaded subsets from
    outliner.

    (NOTE) Yes, currently, the `containerId` attribute is in interface node,
           not in container.

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
    """Return interface node from container node

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
    """Return container node from interface node

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
    """Get top group node name from container node

    Arguments:
        container (str): Name of container node

    """
    # Get all transform nodes from container node
    transforms = cmds.ls(cmds.sets(container, query=True),
                         type="transform",
                         long=True)
    if not transforms:
        return None
    # First member of sorted transform list is the top group node
    return sorted(transforms)[0]


def container_metadata(container):
    """Get additional data from container node

    Arguments:
        container (str): Name of container node

    Returns:
        (dict)

    """
    interface = get_interface_from_container(container)
    # (NOTE) subsetGroup could be None type if it's lookDev or animCurve
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

    Containerizing imported/referenced nodes and creating interface node,
    and the interface node will connected to container node and top group
    node's `message` attribute.

    Arguments:
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host interface
        container_id (str): Container UUID
        nodes (list): Long names of imported/referenced nodes
        ports (list): Long names of nodes for interfacing
        context (dict): Asset information
        cls_name (str): avalon Loader class name
        group_name (str): Top group node of imported/referenced new nodes

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
