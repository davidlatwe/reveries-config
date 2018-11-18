
import os
import json

import avalon.api
import avalon.io
import avalon.maya

from . import lib

from .capsule import namespaced
from .utils import update_id_on_import
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
    from collections import OrderedDict
    from maya import cmds

    interface = cmds.sets(nodes,
                          name=_container_naming(namespace, name, suffix))

    data = OrderedDict()
    data["id"] = AVALON_CONTAINER_INTERFACE_ID
    data["asset"] = context["asset"]["name"]
    data["name"] = name  # subset name
    data["namespace"] = namespace
    data["subsetId"] = str(context["subset"]["_id"])
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


def walk_containers(container):
    """Recursively yield sub-containers
    """
    for con in parse_sub_containers(container):
        yield con

        for sub_con in walk_containers(con):
            yield sub_con


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

    # Update interface data:
    #   subset id,
    #   version, version id,
    #   representation name
    cmds.setAttr(interface + ".subsetId", subset["_id"], type="string")
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

    def process_reference(self, context, name, namespace, group, options):
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

        return True


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

        update_id_on_import(nodes)

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

        return True


def _parse_members_data(entry_path):
    # Load members data
    members_path = entry_path.replace(".abc", ".json")
    with open(os.path.expandvars(members_path), "r") as fp:
        members = json.load(fp)

    return members


def parse_container_members(container):
    current_repr = avalon.io.find_one({
        "_id": avalon.io.ObjectId(container["representation"]),
        "type": "representation"
    })
    package_path = avalon.api.get_representation_path(current_repr)
    entry_file = current_repr["data"]["entry_fname"]
    entry_path = os.path.join(package_path, entry_file)

    return _parse_members_data(entry_path)


class HierarchicalLoader(PackageLoader):
    """Hierarchical referencing based asset loader
    """

    interface = []

    def file_path(self, file_name):
        entry_path = os.path.join(self.package_path, file_name)
        return _env_embedded_path(entry_path)

    def group_name(self, namespace, name):
        return _subset_group_name(namespace, name)

    def apply_variation(self, data, assembly):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def update_variation(self, data_new, data_old, assembly):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def _get_loaders(self, members):
        """
        """
        def get_representation(representation_id):
            representation = avalon.io.find_one(
                {"_id": avalon.io.ObjectId(representation_id)})

            if representation is None:
                raise RuntimeError("Representation not found, this is a bug.")

            return representation

        collected_loader = dict()

        # Get all loaders
        all_loaders = avalon.api.discover(avalon.api.Loader)
        for data in members:

            representation_id = data["representationId"]

            data["representationDoc"] = get_representation(representation_id)

            if representation_id in collected_loader:
                data["loaderCls"] = collected_loader[representation_id]
                continue

            # Find the compatible loaders
            loaders = avalon.api.loaders_from_representation(
                all_loaders, data["representationDoc"])
            # Get the used loader
            Loader = next((x for x in loaders if
                           x.__name__ == data["loader"]),
                          None)

            if Loader is None:
                self.log.error("Loader is missing.")
                raise RuntimeError("Loader is missing: %s", data["loader"])

            data["loaderCls"] = Loader
            collected_loader[representation_id] = Loader

        return members

    def _parent(self, data, namespace, group_name, vessel):
        """
        """
        import maya.cmds as cmds
        from reveries.maya.lib import to_namespace

        # Parent into the setdress hierarchy
        # Namespace is missing from root node(s), add namespace
        # manually
        root = to_namespace(data["root"], namespace)
        root = cmds.ls(group_name + root, long=True)

        if not len(root) == 1:
            raise RuntimeError("Too many or no parent, this is a bug.")

        root = root[0]
        current_parent = cmds.listRelatives(vessel,
                                            parent=True,
                                            fullPath=True) or []
        if root not in current_parent:
            vessel = cmds.parent(vessel, root, relative=True)[0]

        return vessel

    def _add(self, data, namespace, group_name):
        """
        """
        import maya.cmds as cmds
        from avalon.maya.pipeline import AVALON_CONTAINERS

        representation_doc = data["representationDoc"]
        sub_namespace = namespace + ":" + data["namespace"]
        sub_container = avalon.api.load(data["loaderCls"],
                                        representation_doc,
                                        namespace=sub_namespace)

        sub_interface = get_interface_from_container(sub_container)
        vessel = get_group_from_interface(sub_interface)

        with namespaced(namespace, new=False) as namespace:
            vessel = self._parent(data, namespace, group_name, vessel)
            self.apply_variation(data=data,
                                 assembly=vessel)

        cmds.sets(sub_container, remove=AVALON_CONTAINERS)
        cmds.sets(sub_interface, remove=AVALON_PORTS)

        return sub_container, sub_interface

    def load(self, context, name=None, namespace=None, options=None):

        import maya.cmds as cmds

        load_plugin("Alembic")

        asset = context["asset"]

        representation = context["representation"]
        entry_path = self.file_path(representation["data"]["entry_fname"])

        # Load members data
        members = _parse_members_data(entry_path)
        members = self._get_loaders(members)

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

        update_id_on_import(hierarchy)

        # Load sub-subsets
        sub_containers = []
        sub_interfaces = []
        for data in members:

            sub_container, sub_interface = self._add(data,
                                                     namespace,
                                                     group_name)

            sub_containers.append(sub_container)
            sub_interfaces.append(sub_interface)

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

    def _change(self, container, data_new, data_old, namespace, group_name):
        """
        """
        from avalon.pipeline import get_representation_context

        add_list = []

        is_repr_diff = (
            container["representation"] != data_new["representationId"])

        has_override = (
            data_old["representationId"] != data_new["representationId"])

        if container["loader"] == data_new["loader"]:
            if is_repr_diff and has_override:
                self.log.warning("Your scene had local representation "
                                 "overrides within the set. New "
                                 "representations not loaded for %s.",
                                 container["namespace"])
            else:
                current_repr_id = container["representation"]
                current_repr = get_representation_context(current_repr_id)
                loader = data_new["loaderCls"](current_repr)
                loader.update(container, data_new["representationDoc"])
        else:
            avalon.api.remove(container)
            add_list.append(data_new)

        # Update parenting and matrix
        subcon_name = container["objectName"]
        sub_interface = get_interface_from_container(subcon_name)
        vessel = get_group_from_interface(sub_interface)

        with namespaced(namespace, new=False) as namespace:
            vessel = self._parent(data_new, namespace, group_name, vessel)
            self.update_variation(data_new=data_new,
                                  data_old=data_old,
                                  assembly=vessel)

        return add_list

    def update(self, container, representation):
        """
        """

        import maya.cmds as cmds

        def get_ref_node(ndoe):
            """Find one reference node in the members of objectSet"""
            return next((ndoe for ndoe in cmds.sets(ndoe, query=True)
                         if cmds.nodeType(ndoe) == "reference"), None)

        def abort_alert():
            """Error message box"""
            title = "Update Abort"
            message = ("Imported container not supported; container must be "
                       "referenced.")
            self.log.error(message)
            message_box_error(title, message)

        container_node = container["objectName"]
        interface_node = get_interface_from_container(container_node)

        # Assume asset has been referenced
        reference_node = get_ref_node(container_node)
        if not reference_node:
            abort_alert()
            return

        parents = avalon.io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)
        entry_path = self.file_path(representation["data"]["entry_fname"])

        # Get current sub-containers
        current_subcons = dict()

        for sub_con in parse_sub_containers(container):
            # Assume all sub-asset has been referenced
            if not get_ref_node(sub_con["objectName"]):
                abort_alert()
                return

            sub_ns = sub_con["namespace"].rsplit(":", 1)[-1]
            current_subcons[sub_ns] = sub_con

        # Load members data
        members = _parse_members_data(entry_path)
        members = self._get_loaders(members)

        #
        # Start updating

        # Ensure loaded
        load_plugin("Alembic")

        # Update setdress alembic hierarchy
        hierarchy = cmds.file(entry_path,
                              loadReference=reference_node,
                              returnNewNodes=True,
                              type="Alembic")

        update_id_on_import(hierarchy)

        # Get current members data
        current_members = dict()

        new_namespaces = [data["namespace"] for data in members]
        for data in parse_container_members(container):
            if data["namespace"] not in new_namespaces:
                # Remove
                sub_con = current_subcons[data["namespace"]]
                avalon.api.remove(sub_con)
            else:
                namespace = data.pop("namespace")
                current_members[namespace] = data

        # Update sub-subsets
        namespace = container["namespace"]
        group_name = self.group_name(namespace, container["name"])

        add_list = []
        for data in members:
            sub_ns = data["namespace"]
            if sub_ns in current_members:
                # Update
                subcon = current_subcons[sub_ns]
                data_old = current_members[sub_ns]
                add_list += self._change(subcon,
                                         data,
                                         data_old,
                                         namespace,
                                         group_name)

            else:
                add_list.append(data)

        for data in add_list:
            # Add
            sub_container, sub_interface = self._add(data,
                                                     namespace,
                                                     group_name)
            cmds.sets(sub_container, forceElement=container_node)
            cmds.sets(sub_interface, forceElement=interface_node)

        # TODO: Add all new nodes in the reference to the container
        #   Currently new nodes in an updated reference are not added to the
        #   container whereas actually they should be!
        nodes = cmds.referenceQuery(reference_node, nodes=True, dagPath=True)
        cmds.sets(nodes, forceElement=container_node)

        # Update container
        version, subset, asset, _ = parents
        update_container(container_node,
                         asset,
                         subset,
                         version,
                         representation)

    def remove(self, container):
        """
        """
        import maya.cmds as cmds

        # Remove all members
        sub_containers = parse_sub_containers(container)
        for sub_con in sub_containers:
            self.log.info("Removing container %s", sub_con["objectName"])
            avalon.api.remove(sub_con)

        # Remove alembic hierarchy reference
        # TODO: Check whether removing all contained references is safe enough
        members = cmds.sets(container["objectName"], query=True) or []
        references = cmds.ls(members, type="reference")
        for reference in references:
            self.log.info("Removing %s", reference)
            fname = cmds.referenceQuery(reference, filename=True)
            cmds.file(fname, removeReference=True)

        # Delete container and its contents
        if cmds.objExists(container["objectName"]):
            members = cmds.sets(container["objectName"], query=True) or []
            cmds.delete([container["objectName"]] + members)

        return True


class MayaSelectInvalidAction(SelectInvalidAction):

    def select(self, invalid):
        from maya import cmds
        cmds.select(invalid, replace=True, noExpand=True)

    def deselect(self):
        from maya import cmds
        cmds.select(deselect=True)
