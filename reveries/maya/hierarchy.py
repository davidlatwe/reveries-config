
import contextlib
import logging
import avalon.io

from maya import cmds
from avalon.maya.pipeline import (
    AVALON_CONTAINER_ID,
    AVALON_CONTAINERS,
)

from ..plugins import message_box_error

from . import lib
from . import capsule
from .pipeline import parse_container


_log = logging.getLogger("reveries.maya.hierarchy")


def get_sub_container_nodes(container):
    """Get the Avalon containers in this container (node only)

    Args:
        container (dict): The container dict.

    Returns:
        list: A list of child container node names.

    """
    containers = []
    namespace = container["namespace"] + ":"

    for node in lib.lsAttrs({"id": AVALON_CONTAINER_ID}, namespace=namespace):
        containers.append(node)
    return containers


def parse_sub_containers(container):
    """Get the Avalon containers in this container

    Args:
        container (dict): The container dict.

    Returns:
        list: A list of member container dictionaries.

    """
    # Get avalon containers in this package setdress container
    containers = []
    namespace = container["namespace"] + ":"

    for node in lib.lsAttrs({"id": AVALON_CONTAINER_ID}, namespace=namespace):
        member_container = parse_container(node)
        containers.append(member_container)

    return containers


def walk_containers(container):
    """Recursively yield input container's sub-containers

    Args:
        container (dict): The container dict.

    Yields:
        dict: sub-container

    """
    for con in parse_sub_containers(container):
        yield con
        for sub_con in walk_containers(con):
            yield sub_con


def climb_container_id(container):
    """Recursively yield container ID from buttom(leaf) to top(root)

    Args:
        container (str): The container node name

    Yields:
        str: container id

    """
    parents = cmds.ls(cmds.listSets(object=container), type="objectSet")
    for m in parents:
        # Find container node
        if (lib.hasAttr(m, "id") and
                cmds.getAttr(m + ".id") == AVALON_CONTAINER_ID):

            yield cmds.getAttr(m + ".containerId")
            # Next parent
            for n in climb_container_id(m):
                yield n


def walk_container_id(container):
    """Recursively yield container ID from top(root) to buttom(leaf)

    Args:
        container (str): The container node name

    Yields:
        str: container id

    """
    parents = cmds.ls(cmds.listSets(object=container), type="objectSet")
    for m in parents:
        # Find container node
        if (lib.hasAttr(m, "id") and
                cmds.getAttr(m + ".id") == AVALON_CONTAINER_ID):
            # Find next parent before yielding `containerId`
            for n in walk_container_id(m):
                yield n

    yield cmds.getAttr(container + ".containerId")


def container_to_id_path(container):
    """Return the id path of the container

    Args:
        container (dict): The container dict.

    Returns:
        str: container id path

    """
    return "|".join(walk_container_id(container["objectName"]))


def container_from_id_path(container_id_path, parent_namespace):
    """Find container node from container id path

    Args:
        container_id_path (str): The container id path
        parent_namespace (str): Namespace

    Returns:
        str: container node name

    """
    container_ids = container_id_path.split("|")

    leaf_containers = lib.lsAttr("containerId",
                                 container_ids.pop(),  # leaf container id
                                 parent_namespace + "::")

    walkers = {leaf: climb_container_id(leaf) for leaf in leaf_containers}

    while container_ids:
        con_id = container_ids.pop()
        next_walkers = dict()

        for leaf, walker in walkers.items():
            _id = next(walker)
            if con_id == _id:
                next_walkers[leaf] = walker

        walkers = next_walkers

        if len(walkers) == 1:
            break

    if len(walkers) > 1:
        raise RuntimeError("Container not unique, this is a bug.")
    if not len(walkers):
        raise RuntimeError("Container not found, this is a bug.")

    container = next(iter(walkers.keys()))

    return container


_cached_representations = dict()


def get_representation(representation_id):
    """
    """
    try:

        return _cached_representations[representation_id]

    except KeyError:
        representation = avalon.io.find_one(
            {"_id": avalon.io.ObjectId(representation_id)})

        if representation is None:
            raise RuntimeError("Representation not found, this is a bug.")

        _cached_representations[representation_id] = representation

        return representation


_cached_loaders = dict()


def get_loader(loader_name, representation_id):
    """
    """
    try:

        return _cached_loaders[representation_id]

    except KeyError:
        # Get all loaders
        all_loaders = avalon.api.discover(avalon.api.Loader)
        # Find the compatible loaders
        loaders = avalon.api.loaders_from_representation(
            all_loaders, get_representation(representation_id))
        # Get the used loader
        Loader = next((x for x in loaders if
                       x.__name__ == loader_name),
                      None)

        if Loader is None:
            raise RuntimeError("Loader is missing: %s", loader_name)

        _cached_loaders[representation_id] = Loader

        return Loader


def _attach_subset(slot, namespace, root, subset_group):
    """Attach into the setdress hierarchy
    """
    # Namespace is missing from root node(s), add namespace
    # manually
    slot = lib.to_namespace(slot, namespace)
    slot = cmds.ls(root + slot, long=True)

    if not len(slot) == 1:
        raise RuntimeError("Too many or no parent, this is a bug.")

    slot = slot[0]
    current_parent = cmds.listRelatives(subset_group,
                                        parent=True,
                                        fullPath=True) or []
    if slot not in current_parent:
        subset_group = cmds.parent(subset_group, slot, relative=True)[0]

    return subset_group


@contextlib.contextmanager
def add_subset(data, namespace, root, on_update=None):
    """
    """
    sub_namespace = namespace + ":" + data["namespace"]
    options = {
        "containerId": data["containerId"],
        "hierarchy": data["hierarchy"],
    }

    sub_container = avalon.api.load(data["loaderCls"],
                                    data["representationDoc"],
                                    namespace=sub_namespace,
                                    options=options)
    subset_group = sub_container["subsetGroup"]

    try:

        with capsule.namespaced(namespace, new=False) as namespace:
            subset_group = _attach_subset(data["slot"],
                                          namespace,
                                          root,
                                          subset_group)
            sub_container["subsetGroup"] = subset_group

            yield sub_container

    finally:

        if on_update is None:
            cmds.sets(sub_container["objectName"], remove=AVALON_CONTAINERS)
        else:
            container = on_update
            cmds.sets(sub_container["objectName"],
                      forceElement=container["objectName"])


def get_updatable_containers(container):
    """Get sub-containers and ensure they are updatable
    """
    updatable_import_loaders = (
        "ArnoldAssLoader",
        "AnimationLoader",
        "ArnoldVolumeLoader",
        "AtomsCrowdCacheLoader",
    )

    def get_ref_node(node):
        """Find one reference node in the members of objectSet"""
        members = cmds.sets(node, query=True)
        return next(iter(lib.get_reference_nodes(members)), None)

    def abort_alert(name):
        """Error message box"""
        title = "Abort"
        message = ("Found not updatable child subset %s, abort." % name)
        _log.error(message)
        message_box_error(title, message)

        raise RuntimeError(message)

    # Get current sub-containers
    current_subcons = dict()

    for sub_con in parse_sub_containers(container):
        if not get_ref_node(sub_con["objectName"]):
            loader = sub_con["loader"]
            if loader not in updatable_import_loaders:
                abort_alert(sub_con["objectName"])

        sub_ns = sub_con["namespace"].rsplit(":", 1)[-1]
        current_subcons[sub_ns] = sub_con

    return current_subcons


@contextlib.contextmanager
def change_subset(container, data, namespace, root):
    """
    """
    from avalon.pipeline import get_representation_context

    if data["representation"] != container["representation"]:
        current_repr = get_representation_context(container["representation"])
        loader = data["loaderCls"](current_repr)
        loader.update(container, data["representationDoc"])

    try:
        # Update parenting and matrix
        with capsule.namespaced(namespace, new=False) as namespace:
            subset_group = _attach_subset(data["slot"],
                                          namespace,
                                          root,
                                          container["subsetGroup"])
            container["subsetGroup"] = subset_group

            yield container

    finally:
        pass
