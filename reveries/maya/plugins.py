
import os
import json
from collections import OrderedDict

import avalon.api
import avalon.io
import avalon.maya

from . import lib

from .capsule import namespaced
from ..utils import get_representation_path_
from ..plugins import (
    PackageLoader,
    message_box_error,
    SelectInvalidAction,
)


AVALON_PORTS = ":AVALON_PORTS"

AVALON_CONTAINER_INTERFACE_ID = "pyblish.avalon.interface"
AVALON_VESSEL_ATTR = "vessel"
AVALON_CONTAINER_ATTR = "container"


REPRS_PLUGIN_MAPPING = {
    "Alembic": "AbcImport.mll",
    "FBXCache": "fbxmaya.mll",
    "FBX": "fbxmaya.mll",
    "GPUCache": "gpuCache.mll",
}


def _subset_group_name(namespace, name):
    return "{}:{}".format(namespace, name)


def _container_naming(namespace, name, suffix):
    return "%s_%s_%s" % (namespace, name, suffix)


def load_plugin(representation):
    """Load required maya plug-ins base on representation

    Should run this before Loader to `load`, `update`, `switch`

    """
    import maya.cmds as cmds
    try:
        plugin = REPRS_PLUGIN_MAPPING[representation]
    except KeyError:
        pass
    else:
        cmds.loadPlugin(plugin, quiet=True)


def ls_interfaces():
    """List interfaces from active Maya scene"""

    interfaces = lib.lsAttr("id", AVALON_CONTAINER_INTERFACE_ID)
    for interface in sorted(interfaces):
        yield parse_interface(interface)


def ls_vessels():
    """List vessels from active Maya scene"""

    interfaces = lib.lsAttr("id", AVALON_CONTAINER_INTERFACE_ID)
    for interface in sorted(interfaces):
        yield get_group_from_interface(interface)


def subset_interfacing(name,
                       namespace,
                       nodes,
                       context,
                       loader,
                       suffix="PORT"):
    """Expose crucial `nodes` as an interface of a subset container

    Interfacing enables a faster way to access nodes of loaded subsets from
    outliner.

    Arguments:
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host interface
        nodes (list): Long names of nodes for interfacing
        context (dict): Asset information
        suffix (str, optional): Suffix of interface, defaults to `_PORT`.

    Returns:
        interface (str): Name of interface assembly

    """
    from maya import cmds

    interface = cmds.sets(nodes,
                          name=_container_naming(namespace, name, suffix))

    data = OrderedDict()
    data["id"] = AVALON_CONTAINER_INTERFACE_ID
    data["asset"] = context["asset"]["name"]
    data["name"] = name
    data["namespace"] = namespace
    data["version"] = context["version"]["name"]
    data["versionId"] = str(context["version"]["_id"])
    data["representation"] = context["representation"]["name"]
    data["representationId"] = str(context["representation"]["_id"])
    data["loader"] = loader

    avalon.maya.lib.imprint(interface, data)

    main_interface = cmds.ls(AVALON_PORTS, type="objectSet")
    if not main_interface:
        main_interface = cmds.sets(empty=True, name=AVALON_PORTS)
    else:
        main_interface = main_interface[0]

    cmds.sets(interface, addElement=main_interface)

    return interface


def parse_interface(interface):
    """Read attributes from interface node for package dumping

    Arguments:
        interface (str): Name of interface node

    Returns:
        dict: The interface data for this interface node.

    """
    data = avalon.maya.read(interface)
    data["objectName"] = interface

    return data


def parse_sub_containers(container):
    """Get the Avalon containers in this container

    Args:
        container (dict): The container dict.

    Returns:
        list: A list of member container dictionaries.

    """
    import maya.cmds as cmds
    import avalon.schema
    from avalon.maya.pipeline import parse_container

    # Get avalon containers in this package setdress container
    containers = []
    members = cmds.sets(container["objectName"], query=True)
    for node in cmds.ls(members, type="objectSet"):
        try:
            member_container = parse_container(node)
            containers.append(member_container)
        except avalon.schema.ValidationError:
            pass

    return containers


def get_interface_from_container(container):
    """Return interface node of container

    Raise `RuntimeError` if getting none or more then one interface.

    Arguments:
        container (str): Name of container node

    Returns a str

    """
    import maya.cmds as cmds

    representation = cmds.getAttr(container + ".representation")
    namespace = cmds.getAttr(container + ".namespace")

    nodes = lib.lsAttrs({
        "id": AVALON_CONTAINER_INTERFACE_ID,
        "representationId": representation,
        "namespace": namespace})

    if not len(nodes) == 1:
        raise RuntimeError("Container has none or more then one interface, "
                           "this is a bug.")

    return nodes[0]


def get_group_from_interface(interface):
    """Return group node of interface

    Raise `RuntimeError` if no group found.

    Arguments:
        interface (str): Name of interface node

    Returns a str

    """
    import maya.cmds as cmds

    group = cmds.listConnections(interface + "." + AVALON_VESSEL_ATTR,
                                 source=True,
                                 destination=False,
                                 type="transform")
    if not group:
        raise RuntimeError("Can not get group node, this is a bug.")

    return cmds.ls(group, long=True)[0]


def update_container(container, asset, subset, version, representation):
    """
    """
    import maya.cmds as cmds

    asset_changed = False
    subset_changed = False

    interface = get_interface_from_container(container)

    # Update representation id
    cmds.setAttr(container + ".representation",
                 str(representation["_id"]),
                 type="string")
    cmds.setAttr(interface + ".representationId",
                 str(representation["_id"]),
                 type="string")

    origin_asset = cmds.getAttr(interface + ".asset")
    update_asset = asset["name"]

    namespace = cmds.getAttr(interface + ".namespace")
    if not origin_asset == update_asset:
        asset_changed = True
        # Update namespace
        new_namespace = _unique_root_namespace(update_asset)
        cmds.namespace(parent=":", rename=(namespace, new_namespace[1:]))
        namespace = new_namespace
        # Update data
        cmds.setAttr(container + ".namespace", namespace, type="string")
        cmds.setAttr(interface + ".namespace", namespace, type="string")
        cmds.setAttr(interface + ".asset", update_asset, type="string")

    origin_subset = cmds.getAttr(interface + ".name")
    update_subset = subset["name"]

    name = origin_subset
    if not origin_subset == update_subset:
        subset_changed = True
        name = subset["name"]
        # Rename group node
        group = get_group_from_interface(interface)
        group = cmds.rename(
            group, _subset_group_name(namespace, name))
        # Update data
        cmds.setAttr(container + ".name", name, type="string")
        cmds.setAttr(interface + ".name", name, type="string")

    if any((asset_changed, subset_changed)):
        # Rename container
        container = cmds.rename(
            container, _container_naming(namespace, name, "CON"))
        # Rename interface
        interface = cmds.rename(
            interface, _container_naming(namespace, name, "PORT"))

    # Update interface data: version, version id, representation name
    cmds.setAttr(interface + ".version", version["name"])
    cmds.setAttr(interface + ".versionId",
                 version["_id"],
                 type="string")
    cmds.setAttr(interface + ".representation",
                 representation["name"],
                 type="string")


def _env_embedded_path(file_path):
    """Embed environment var `$AVALON_PROJECTS` into file path

    This will ensure reference or cache path resolvable when project root
    moves to other place.

    """
    if not os.path.isfile(file_path):
        raise IOError("File Not Found: {!r}".format(file_path))

    file_path = file_path.replace(
        avalon.api.registered_root(), "$AVALON_PROJECTS"
    )

    return file_path


def _subset_containerising(name, namespace, nodes, ports, context,
                           cls_name, group_name):
    """Containerise loaded subset and build interface
    """
    from avalon.maya.pipeline import containerise
    from reveries.maya.lib import connect_message

    interface = subset_interfacing(name=name,
                                   namespace=namespace,
                                   nodes=ports,
                                   context=context,
                                   loader=cls_name)
    container = containerise(name=name,
                             namespace=namespace,
                             nodes=nodes,
                             context=context,
                             loader=cls_name)
    # interface -> top_group.message
    #           -> container.message
    connect_message(group_name, interface, AVALON_VESSEL_ATTR)
    connect_message(container, interface, AVALON_CONTAINER_ATTR)

    return container


def _unique_root_namespace(asset_name):
    from avalon.maya import lib
    unique = lib.unique_namespace(
        asset_name + "_",
        prefix="_" if asset_name[0].isdigit() else "",
        suffix="_",
    )
    return ":" + unique  # Ensure in root


class ReferenceLoader(PackageLoader):
    """A basic ReferenceLoader for Maya

    This will implement the basic behavior for a loader to inherit from that
    will containerize the reference and will implement the `remove` and
    `update` logic.

    """

    interface = []

    def file_path(self, file_name):
        entry_path = os.path.join(self.package_path, file_name)
        return _env_embedded_path(entry_path)

    def group_name(self, namespace, name):
        return _subset_group_name(namespace, name)

    def process_reference(self, context, name, namespace, options):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def load(self, context, name=None, namespace=None, options=None):

        load_plugin(context["representation"]["name"])

        asset = context["asset"]

        namespace = namespace or _unique_root_namespace(asset["name"])

        group_name = self.group_name(namespace, name)

        self.process_reference(context=context,
                               name=name,
                               namespace=namespace,
                               group=group_name,
                               options=options)

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        if not nodes:
            return

        container = _subset_containerising(name=name,
                                           namespace=namespace,
                                           nodes=nodes,
                                           ports=self.interface,
                                           context=context,
                                           cls_name=self.__class__.__name__,
                                           group_name=group_name)

        return container

    def update(self, container, representation):
        from maya import cmds

        node = container["objectName"]

        # Assume asset has been referenced
        reference_node = next((node for node in cmds.sets(node, query=True)
                               if cmds.nodeType(node) == "reference"), None)

        if not reference_node:
            title = "Update Abort"
            message = ("Imported container not supported; container must be "
                       "referenced.")
            self.log.error(message)
            message_box_error(title, message)
            return

        load_plugin(representation["name"])

        file_type = representation["name"]
        if file_type == "FBXCache":
            file_type = "FBX"
        elif file_type == "GPUCache":
            file_type = "MayaAscii"

        parents = avalon.io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)

        entry_path = self.file_path(representation["data"]["entry_fname"])

        cmds.file(entry_path,
                  loadReference=reference_node,
                  type=file_type,
                  defaultExtensions=False)

        # TODO: Add all new nodes in the reference to the container
        #   Currently new nodes in an updated reference are not added to the
        #   container whereas actually they should be!
        nodes = cmds.referenceQuery(reference_node, nodes=True, dagPath=True)
        cmds.sets(nodes, forceElement=node)

        # Update container
        version, subset, asset, _ = parents
        update_container(node, asset, subset, version, representation)

    def remove(self, container):
        """Remove an existing `container` from Maya scene

        Arguments:
            container (avalon-core:container-1.0): Which container
                to remove from scene.

        """
        from maya import cmds

        node = container["objectName"]

        # Assume asset has been referenced
        reference_node = next((node for node in cmds.sets(node, query=True)
                               if cmds.nodeType(node) == "reference"), None)

        if not reference_node:
            title = "Remove Abort"
            message = ("Imported container not supported; container must be "
                       "referenced.")
            self.log.error(message)
            message_box_error(title, message)
            return

        self.log.info("Removing '%s' from Maya.." % container["name"])

        namespace = cmds.referenceQuery(reference_node, namespace=True)
        fname = cmds.referenceQuery(reference_node, filename=True)
        cmds.file(fname, removeReference=True)

        try:
            cmds.delete(node)
        except ValueError:
            # Already implicitly deleted by Maya upon removing reference
            pass

        try:
            # If container is not automatically cleaned up by May (issue #118)
            cmds.namespace(removeNamespace=namespace,
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass


class ImportLoader(PackageLoader):

    interface = []

    def file_path(self, file_name):
        entry_path = os.path.join(self.package_path, file_name)
        return _env_embedded_path(entry_path)

    def group_name(self, namespace, name):
        return _subset_group_name(namespace, name)

    def process_import(self, context, name, namespace, options):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def load(self, context, name=None, namespace=None, options=None):

        load_plugin(context["representation"]["name"])

        asset = context['asset']

        namespace = namespace or _unique_root_namespace(asset["name"])

        group_name = self.group_name(namespace, name)

        self.process_import(context=context,
                            name=name,
                            namespace=namespace,
                            group=group_name,
                            options=options)

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        if not nodes:
            return

        container = _subset_containerising(name=name,
                                           namespace=namespace,
                                           nodes=nodes,
                                           ports=self.interface,
                                           context=context,
                                           cls_name=self.__class__.__name__,
                                           group_name=group_name)

        return container

    def update(self, container, representation):

        title = "Can Not Update"
        message = ("The content of this asset was imported. "
                   "We cannot update this because we will need"
                   " to keep insane amount of things in mind.\n"
                   "Please remove and reimport the asset."
                   "\n\nIf you really need to update a lot we "
                   "recommend referencing.")
        self.log.error(message)
        message_box_error(title, message)
        return

    def remove(self, container):

        from maya import cmds

        namespace = container["namespace"]
        container_name = container["objectName"]

        container_content = cmds.sets(container_name, query=True)
        nodes = cmds.ls(container_content, long=True)

        nodes.append(container_name)

        self.log.info("Removing '%s' from Maya.." % container["name"])

        try:
            cmds.delete(nodes)
        except ValueError:
            pass

        cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)


def _parse_instance_data(entry_path):
    # Load instances data
    instances_path = entry_path.replace(".abc", ".json")
    with open(os.path.expandvars(instances_path), "r") as fp:
        instances = json.load(fp)

    return instances


def parse_container_instances(container):
    current_repr = avalon.io.find_one({
        "_id": avalon.io.ObjectId(container["representation"]),
        "type": "representation"
    })
    package_path = avalon.api.get_representation_path(current_repr)
    entry_file = current_repr["data"]["entry_fname"]
    entry_path = os.path.join(package_path, entry_file)

    return _parse_instance_data(entry_path)


class NestedLoader(PackageLoader):
    """Hierarchical referencing loader
    """

    interface = []
    sub_representations = []

    def file_path(self, file_name):
        entry_path = os.path.join(self.package_path, file_name)
        return _env_embedded_path(entry_path)

    def group_name(self, namespace, name):
        return _subset_group_name(namespace, name)

    def process_subset(self, instance, assembly):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def _select_representations(self, instances):
        """
        """
        collected_loader = dict()

        # Get all loaders
        all_loaders = avalon.api.discover(avalon.api.Loader)
        for data in instances:

            version_id = data["versionId"]

            if version_id in collected_loader:
                data["loader_cls"] = collected_loader[version_id]
                continue

            # Select representation
            repr_name = data["representation"]
            representation_id = None
            if repr_name not in self.sub_representations:
                for name in self.sub_representations:
                    _filter = {"type": "representation",
                               "name": name,
                               "parent": version_id}
                    project = {"_id": True}
                    representation = avalon.io.find_one(_filter, project)
                    if representation is not None:
                        representation_id = representation["_id"]
                        data["representationId"] = representation_id
                        break

            if representation_id is None:
                raise RuntimeError("Representation not found.")

            # Find the compatible loaders
            loaders = avalon.api.loaders_from_representation(
                all_loaders, representation_id)
            # Get the used loader
            loader_name = data["loader"]
            Loader = next((x for x in loaders if
                           x.__name__ == loader_name),
                          None)

            if Loader is None:
                self.log.error("Loader is missing.")
                raise RuntimeError("Loader is missing: %s", loader_name)

            data["loader_cls"] = Loader
            collected_loader[version_id] = Loader

        return instances

    def load(self, context, name=None, namespace=None, options=None):

        import maya.cmds as cmds
        from avalon.maya.pipeline import AVALON_CONTAINERS
        from reveries.maya.lib import to_namespace

        load_plugin("Alembic")

        asset = context["asset"]

        representation = context["representation"]
        entry_path = self.file_path(representation["data"]["entry_fname"])

        # Load instances data
        instances = _parse_instance_data(entry_path)
        instances = self._select_representations(instances)

        namespace = namespace or _unique_root_namespace(asset["name"])
        group_name = self.group_name(namespace, name)

        # Load the setdress alembic hierarchy
        hierarchy = cmds.file(entry_path,
                              reference=True,
                              namespace=namespace,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName=group_name,
                              typ="Alembic")

        # Load sub-subsets
        sub_containers = []
        sub_interfaces = []
        for data in instances:

            representation_id = data["representationId"]
            sub_namespace = namespace + ":" + data["namespace"]
            sub_container = avalon.api.load(data["loader_cls"],
                                            representation_id,
                                            namespace=sub_namespace)

            sub_interface = get_interface_from_container(sub_container)
            vessel = get_group_from_interface(sub_interface)

            with namespaced(namespace, new=False) as namespace:

                # Parent into the setdress hierarchy
                # Namespace is missing from root node(s), add namespace
                # manually
                root = to_namespace(data["root"], namespace)
                root = group_name + root
                cmds.parent(vessel, root, relative=True)

                self.process_subset(instance=data,
                                    assembly=vessel)

            sub_containers.append(sub_container)
            sub_interfaces.append(sub_interface)

            cmds.sets(sub_container, remove=AVALON_CONTAINERS)
            cmds.sets(sub_interface, remove=AVALON_PORTS)

        self[:] = hierarchy + sub_containers
        self.interface = [group_name] + sub_interfaces

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        if not nodes:
            return

        container = _subset_containerising(name=name,
                                           namespace=namespace,
                                           nodes=nodes,
                                           ports=self.interface,
                                           context=context,
                                           cls_name=self.__class__.__name__,
                                           group_name=group_name)

        return container

    def update(self, container, representation):
        pass

    def remove(self, container):
        pass


class MayaSelectInvalidAction(SelectInvalidAction):

    def select(self, invalid):
        from maya import cmds
        cmds.select(invalid, replace=True, noExpand=True)

    def deselect(self):
        from maya import cmds
        cmds.select(deselect=True)
