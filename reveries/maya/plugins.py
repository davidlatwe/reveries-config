
import os
from collections import OrderedDict

import avalon.api
import avalon.maya.lib

from . import lib

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


def container_interfacing(name,
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

    interface = cmds.sets(nodes, name="%s_%s_%s" % (namespace, name, suffix))

    data = OrderedDict()
    data["id"] = AVALON_CONTAINER_INTERFACE_ID
    data["asset"] = context["asset"]["name"]
    data["name"] = name
    data["namespace"] = namespace
    data["version"] = context["version"]["name"]
    data["representation"] = context["representation"]["name"]
    data["representation_id"] = str(context["representation"]["_id"])
    data["loader"] = loader

    avalon.maya.lib.imprint(interface, data)

    main_interface = cmds.ls(AVALON_PORTS, type="objectSet")
    if not main_interface:
        main_interface = cmds.sets(empty=True, name=AVALON_PORTS)
    else:
        main_interface = main_interface[0]

    cmds.sets(interface, addElement=main_interface)

    return interface


def read_interface_to_package(interface):
    """Read attributes from interface node for package dumping

    Arguments:
        interface (str): Name of interface node

    Returns:
        _id (str): representation id
        data (dict): {name: str, loader: str}

    """
    import maya.cmds as cmds

    _id = cmds.getAttr(interface + ".representation_id")
    name = cmds.getAttr(interface + ".name")
    loader = cmds.getAttr(interface + ".loader")

    return _id, dict(name=name, loader=loader)


def parse_interface_from_container(container):
    """Return interface node of container

    Arguments:
        container (str): Name of container node

    Returns a str

    """
    import maya.cmds as cmds

    representation = cmds.getAttr(container + ".representation")
    namespace = cmds.getAttr(container + ".namespace")

    nodes = lib.lsAttrs({
        "id": AVALON_CONTAINER_INTERFACE_ID,
        "representation_id": representation,
        "namespace": namespace})

    if not len(nodes) == 1:
        raise RuntimeError("Container has none or more then one interface, "
                           "this is a bug.")

    return nodes[0]


def parse_group_from_interface(interface):
    """Return group node of interface

    Arguments:
        interface (str): Name of interface node

    Returns a str

    """
    import maya.cmds as cmds

    group = cmds.listConnections(interface + "." + AVALON_VESSEL_ATTR,
                                 source=True,
                                 destination=False,
                                 type="transform") or []
    if not group:
        raise RuntimeError("Can not get group node, this is a bug.")

    return group[0]


def parse_group_from_container(container):
    """Return group node of container

    Arguments:
        container (str): Name of container node

    Returns a str

    """
    interface = parse_interface_from_container(container)
    return parse_group_from_interface(interface)


class ReferenceLoader(PackageLoader):
    """A basic ReferenceLoader for Maya

    This will implement the basic behavior for a loader to inherit from that
    will containerize the reference and will implement the `remove` and
    `update` logic.

    """

    interface = []

    def file_path(self, file_name):
        entry_path = os.path.join(self.package_path, file_name)

        # This will ensure reference path resolvable when project root moves to
        # other place.
        entry_path = entry_path.replace(
            avalon.api.registered_root(), "$AVALON_PROJECTS"
        )

        return entry_path

    def process_reference(self, context, name, namespace, options):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def load(self, context, name=None, namespace=None, options=None):
        from avalon.maya import lib
        from avalon.maya.pipeline import containerise
        from reveries.maya.lib import connect_message

        load_plugin(context["representation"]["name"])

        asset = context["asset"]

        namespace = namespace or lib.unique_namespace(
            asset["name"] + "_",
            prefix="_" if asset["name"][0].isdigit() else "",
            suffix="_",
        )

        group_name = self.process_reference(context=context,
                                            name=name,
                                            namespace=namespace,
                                            options=options)

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        if not nodes:
            return

        interface = container_interfacing(name=name,
                                          namespace=namespace,
                                          nodes=self.interface,
                                          context=context,
                                          loader=self.__class__.__name__)

        container = containerise(name=name,
                                 namespace=namespace,
                                 nodes=nodes,
                                 context=context,
                                 loader=self.__class__.__name__)

        connect_message(group_name, interface, AVALON_VESSEL_ATTR)
        connect_message(container, interface, AVALON_CONTAINER_ATTR)

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

        self.package_path = avalon.api.get_representation_path(representation)

        entry_path = self.file_path(representation["data"]["entry_fname"])

        cmds.file(entry_path, loadReference=reference_node, type=file_type)

        # TODO: Add all new nodes in the reference to the container
        #   Currently new nodes in an updated reference are not added to the
        #   container whereas actually they should be!
        nodes = cmds.referenceQuery(reference_node, nodes=True, dagPath=True)
        cmds.sets(nodes, forceElement=node)

        # Update metadata
        cmds.setAttr(node + ".representation",
                     str(representation["_id"]),
                     type="string")

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

    def __init__(self, context):
        super(ImportLoader, self).__init__(context)

        # This will ensure reference path resolvable when project root moves to
        # other place.
        self.package_path = self.package_path.replace(
            avalon.api.registered_root(), "$AVALON_PROJECTS"
        )

    def process_import(self, context, name, namespace, options):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def load(self, context, name=None, namespace=None, options=None):
        from avalon.maya import lib
        from avalon.maya.pipeline import containerise
        from reveries.maya.lib import connect_message

        load_plugin(context["representation"]["name"])

        asset = context['asset']

        namespace = namespace or lib.unique_namespace(
            asset["name"] + "_",
            prefix="_" if asset["name"][0].isdigit() else "",
            suffix="_",
        )

        group_name = self.process_import(context=context,
                                         name=name,
                                         namespace=namespace,
                                         options=options)

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        if not nodes:
            return

        interface = container_interfacing(name=name,
                                          namespace=namespace,
                                          nodes=self.interface,
                                          context=context,
                                          loader=self.__class__.__name__)

        container = containerise(name=name,
                                 namespace=namespace,
                                 nodes=nodes,
                                 context=context,
                                 loader=self.__class__.__name__)

        connect_message(group_name, interface, AVALON_VESSEL_ATTR)
        connect_message(container, interface, AVALON_CONTAINER_ATTR)

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


class MayaSelectInvalidAction(SelectInvalidAction):

    def select(self, invalid):
        from maya import cmds
        cmds.select(invalid, replace=True, noExpand=True)

    def deselect(self):
        from maya import cmds
        cmds.select(deselect=True)
