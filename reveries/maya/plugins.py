
import os
import json

import avalon.api
import avalon.io
import avalon.maya

from . import lib

from .utils import (
    update_id_verifiers,
    generate_container_id,
)

from ..utils import get_representation_path_

from ..plugins import (
    PackageLoader,
    message_box_error,
    SelectInvalidInstanceAction,
    SelectInvalidContextAction,
)

from .pipeline import (
    subset_group_name,
    subset_containerising,
    unique_root_namespace,
    update_container,
    env_embedded_path,
)

from .hierarchy import (
    parse_sub_containers,
    get_representation,
    get_loader,
    add_subset,
    change_subset,
    get_referenced_containers,
)


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


class MayaBaseLoader(PackageLoader):

    def __init__(self, context):
        from reveries.maya.pipeline import is_editable
        if not is_editable():
            raise Exception("All nodes has been locked, you may not change "
                            "anything.")
        super(MayaBaseLoader, self).__init__(context)

    def file_path(self, representation):
        file_name = representation["data"]["entryFileName"]
        entry_path = os.path.join(self.package_path, file_name)

        if not os.path.isfile(entry_path):
            raise IOError("File Not Found: {!r}".format(entry_path))

        return env_embedded_path(entry_path)

    def group_name(self, namespace, name):
        group = subset_group_name(namespace, name)
        return group.replace(".", "_")


class ReferenceLoader(MayaBaseLoader):
    """A basic ReferenceLoader for Maya

    This will implement the basic behavior for a loader to inherit from that
    will containerize the reference and will implement the `remove` and
    `update` logic.

    """

    def process_reference(self, context, name, namespace, group, options):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def load(self, context, name=None, namespace=None, options=None):

        from maya import cmds

        options = options or dict()

        count = options.get("count", 1)
        if count > 1:
            options["count"] -= 1
            self.load(context, name, options=options.copy())

        load_plugin(context["representation"]["name"])

        asset = context["asset"]

        asset_name = asset["data"].get("shortName", asset["name"])
        if context["subset"]["schema"] == "avalon-core:subset-3.0":
            families = context["subset"]["data"]["families"]
        else:
            families = context["version"]["data"]["families"]
        family_name = families[0].split(".")[-1]
        namespace = namespace or unique_root_namespace(asset_name, family_name)

        group_name = self.group_name(namespace, name)

        self.process_reference(context=context,
                               name=name,
                               namespace=namespace,
                               group=group_name,
                               options=options)

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        nodes = self._get_containerizable_nodes(nodes)

        # Only containerize if any nodes were loaded by the Loader
        if not nodes:
            return

        if "offset" in options and cmds.objExists(group_name):
            offset = [i * (count - 1) for i in options["offset"]]
            cmds.setAttr(group_name + ".t", *offset)

        container_id = options.get("containerId", generate_container_id())

        container = subset_containerising(name=name,
                                          namespace=namespace,
                                          container_id=container_id,
                                          nodes=nodes,
                                          context=context,
                                          cls_name=self.__class__.__name__,
                                          group_name=group_name)
        return container

    def _get_containerizable_nodes(self, nodes):
        """Filter to only the nodes we want to include in the container"""
        if not nodes:
            # Do nothing if empty list
            return nodes

        from maya import cmds

        # Bug: In Maya instanced referenced meshes lose their shader on scene
        #      open assignments when the shape is in an objectSet. So we
        #      exclude *all!* shape nodes from containerizing to avoid it.
        #      For more information, see:
        #      https://gitter.im/getavalon/Lobby?at=5db97984a03ae1584f367117
        shapes = set(cmds.ls(nodes, shapes=True, long=True))
        return [node for node in cmds.ls(nodes, long=True)
                if node not in shapes]

    def _find_reference_node(self, container):
        from maya import cmds

        node = container["objectName"]
        members = cmds.sets(node, query=True, nodesOnly=True)
        reference_node = lib.get_highest_reference_node(members)
        # cache it
        container["referenceNode"] = reference_node

        return reference_node

    def get_reference_node(self, container):
        reference_node = container.get("referenceNode",
                                       self._find_reference_node(container))
        if reference_node is None:
            raise AssertionError("No reference node found in container")

        return reference_node

    def update(self, container, representation):
        from maya import cmds

        # Flag `_dropRefEdit` from `container` is a workaround
        # should coming from `options`
        drop_edit = container.pop("_dropRefEdit", False)

        node = container["objectName"]

        # Get reference node from container
        reference_node = self.get_reference_node(container)

        load_plugin(representation["name"])

        parents = avalon.io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)

        entry_path = self.file_path(representation)
        self.log.info("Reloading reference from: {!r}".format(entry_path))

        # Representation that use `ReferenceLoader`, either "ma" or "mb"
        file_type = representation["name"]

        # (NOTE) This is a patch for the bad implemenation of Abc wrapping.
        if file_type == "Alembic" and entry_path.endswith(".ma"):
            file_type = "mayaAscii"

        if file_type not in ("mayaBinary", "Alembic"):
            file_type = "mayaAscii"

        if drop_edit:
            cmds.file(unloadReference=reference_node)
            cmds.file(cleanReference=reference_node, editCommand="setAttr")

        cmds.file(entry_path,
                  loadReference=reference_node,
                  type=file_type,
                  defaultExtensions=False)

        # Add new nodes of the reference to the container
        nodes = cmds.referenceQuery(reference_node, nodes=True, dagPath=True)
        nodes = self._get_containerizable_nodes(nodes)
        if nodes:
            cmds.sets(nodes, forceElement=node)

        # Remove any placeHolderList attribute entries from the set that
        # are remaining from nodes being removed from the referenced file.
        # (NOTE) This ensures the reference update correctly when node name
        #   changed (e.g. shadingEngine) in different version.
        holders = (lambda N: [x for x in cmds.sets(N, query=True) or []
                              if ".placeHolderList" in x])
        cmds.sets(holders(node), remove=node)

        # Update container
        version, subset, asset, _ = parents
        update_container(container, asset, subset, version, representation)

    def remove(self, container):
        """Remove an existing `container` from Maya scene

        Arguments:
            container (avalon-core:container-1.0): Which container
                to remove from scene.

        """
        from maya import cmds

        node = container["objectName"]

        # Get reference node from container
        try:
            reference_node = self.get_reference_node(container)
        except AssertionError:
            # Reference node not found, try removing as imported subset
            self.log.info("Removing '%s' from Maya as imported.."
                          % container["name"])
            namespace = container["namespace"]
            container_content = cmds.sets(node, query=True)
            nodes = cmds.ls(container_content, long=True)
            nodes.append(node)
            try:
                cmds.delete(nodes)
            except ValueError:
                pass
            cmds.namespace(removeNamespace=namespace,
                           deleteNamespaceContent=True)
            return True

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


class ImportLoader(MayaBaseLoader):

    def process_import(self, context, name, namespace, options):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def load(self, context, name=None, namespace=None, options=None):

        load_plugin(context["representation"]["name"])

        asset = context['asset']

        asset_name = asset["data"].get("shortName", asset["name"])
        if context["subset"]["schema"] == "avalon-core:subset-3.0":
            families = context["subset"]["data"]["families"]
        else:
            families = context["version"]["data"]["families"]
        family_name = families[0].split(".")[-1]
        namespace = namespace or unique_root_namespace(asset_name, family_name)

        group_name = self.group_name(namespace, name)

        options = options or dict()

        self.process_import(context=context,
                            name=name,
                            namespace=namespace,
                            group=group_name,
                            options=options)

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        if not nodes:
            return

        container_id = options.get("containerId", generate_container_id())

        container = subset_containerising(name=name,
                                          namespace=namespace,
                                          container_id=container_id,
                                          nodes=nodes,
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


class HierarchicalLoader(MayaBaseLoader):
    """Hierarchical referencing based asset loader
    """

    def _members_data_from_container(self, container):
        current_repr = avalon.io.find_one({
            "_id": avalon.io.ObjectId(container["representation"]),
            "type": "representation"
        })
        package_path = avalon.api.get_representation_path(current_repr)
        entry_file = os.path.basename(self.file_path(current_repr))
        entry_path = os.path.join(package_path, entry_file)

        return _parse_members_data(entry_path)

    def apply_variation(self, data, container):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def update_variation(self, data_new, data_old, container, force=False):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def load(self, context, name=None, namespace=None, options=None):

        import maya.cmds as cmds

        load_plugin("Alembic")

        asset = context["asset"]

        representation = context["representation"]
        entry_path = self.file_path(representation)

        # Load members data
        members = _parse_members_data(entry_path)

        options = options or dict()

        if "containerId" in options:
            container_id = options["containerId"]
            hierarchy = options["hierarchy"]

            _members = list()
            for data in members:
                try:
                    sub_hierarchy = hierarchy[data["containerId"]]
                except KeyError:
                    self.log.warning("Asset possibly been removed in parent "
                                     "asset. Container ID: %s",
                                     data["containerId"])
                    continue

                child_ident, member_data = sub_hierarchy.popitem()

                child_ident = child_ident.split("|")
                data["representation"] = child_ident[0]
                data["namespace"] = child_ident[1]
                data["hierarchy"] = member_data

                _members.append(data)

            members = _members

        else:
            container_id = generate_container_id()

        asset_name = asset["data"].get("shortName", asset["name"])
        if context["subset"]["schema"] == "avalon-core:subset-3.0":
            families = context["subset"]["data"]["families"]
        else:
            families = context["version"]["data"]["families"]
        family_name = families[0].split(".")[-1]
        namespace = namespace or unique_root_namespace(asset_name, family_name)
        group_name = self.group_name(namespace, name)

        # Load the setdress alembic hierarchy
        hierarchy = cmds.file(entry_path,
                              reference=True,
                              namespace=namespace,
                              ignoreVersion=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName=group_name,
                              typ="Alembic")

        update_id_verifiers(hierarchy)

        # Load sub-subsets
        sub_containers = []
        for data in members:

            repr_id = data["representation"]
            data["representationDoc"] = get_representation(repr_id)
            data["loaderCls"] = get_loader(data["loader"], repr_id)

            root = group_name
            with add_subset(data, namespace, root) as sub_container:

                self.apply_variation(data=data,
                                     container=sub_container)

            sub_containers.append(sub_container["objectName"])

        self[:] = hierarchy + sub_containers

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        if not nodes:
            return

        container = subset_containerising(name=name,
                                          namespace=namespace,
                                          container_id=container_id,
                                          nodes=nodes,
                                          context=context,
                                          cls_name=self.__class__.__name__,
                                          group_name=group_name)
        return container

    def update(self, container, representation):
        """
        """
        import maya.cmds as cmds

        # Flag `_force_update` from `container` is a workaround
        # should coming from `options`
        force_update = container.pop("_force_update", False)

        # Get and check current sub-containers
        reference_node, current_subcons = get_referenced_containers(container)

        # Load members data
        parents = avalon.io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)
        entry_path = self.file_path(representation)

        members = _parse_members_data(entry_path)

        #
        # Start updating

        # Ensure loaded
        load_plugin("Alembic")

        # Update setdress alembic hierarchy
        hierarchy = cmds.file(entry_path,
                              loadReference=reference_node,
                              returnNewNodes=True,
                              type="Alembic")

        update_id_verifiers(hierarchy)

        # Get current members data
        current_members = dict()
        new_namespaces = set(data_new["namespace"] for data_new in members)

        for data_old in self._members_data_from_container(container):
            namespace_old = data_old["namespace"]

            if namespace_old not in new_namespaces:
                # Remove
                avalon.api.remove(current_subcons.pop(namespace_old))
            else:
                current_members[namespace_old] = data_old

        # Update sub-subsets
        namespace = container["namespace"]
        group_name = self.group_name(namespace, container["name"])

        add_list = []
        for data_new in members:

            repr_id = data_new["representation"]
            data_new["representationDoc"] = get_representation(repr_id)
            data_new["loaderCls"] = get_loader(data_new["loader"], repr_id)

            sub_ns = data_new["namespace"]

            if sub_ns in current_members:
                sub_container = current_subcons[sub_ns]
                data_old = current_members[sub_ns]

                is_repr_diff = (data_old["representation"] !=
                                data_new["representation"])
                has_override = (data_old["representation"] !=
                                sub_container["representation"])

                if sub_container["loader"] == data_new["loader"]:

                    if is_repr_diff and has_override and not force_update:
                        self.log.warning("Your scene had local representation "
                                         "overrides within the set. New "
                                         "representations not loaded for %s.",
                                         sub_container["namespace"])

                    else:
                        # Update
                        root = group_name
                        with change_subset(sub_container,
                                           data_new,
                                           namespace,
                                           root) as sub_container:

                            self.update_variation(data_new=data_new,
                                                  data_old=data_old,
                                                  container=sub_container,
                                                  force=force_update)
                else:
                    # Update
                    # But Loaders are different, remove first, add later
                    avalon.api.remove(sub_container)
                    add_list.append(data_new)

            else:
                add_list.append(data_new)

        for data in add_list:
            # Add
            root = group_name
            on_update = container
            with add_subset(data, namespace, root, on_update) as sub_container:

                self.apply_variation(data=data,
                                     container=sub_container)

        # TODO: Add all new nodes in the reference to the container
        #   Currently new nodes in an updated reference are not added to the
        #   container whereas actually they should be!
        nodes = cmds.referenceQuery(reference_node, nodes=True, dagPath=True)
        cmds.sets(nodes, forceElement=container["objectName"])

        # Update container
        version, subset, asset, _ = parents
        update_container(container,
                         asset,
                         subset,
                         version,
                         representation)

    def remove(self, container):
        """
        """
        import maya.cmds as cmds
        from reveries.maya import lib

        # Remove all members
        sub_containers = parse_sub_containers(container)
        for sub_con in sub_containers:
            self.log.info("Removing container %s", sub_con["objectName"])
            avalon.api.remove(sub_con)

        # Remove alembic hierarchy reference
        # TODO: Check whether removing all contained references is safe enough
        members = cmds.sets(container["objectName"], query=True) or []
        references = lib.get_reference_nodes(members)
        for reference in references:
            self.log.info("Removing %s", reference)
            fname = cmds.referenceQuery(reference, filename=True)
            cmds.file(fname, removeReference=True)

        # Delete container and its contents
        if cmds.objExists(container["objectName"]):
            members = cmds.sets(container["objectName"], query=True) or []
            cmds.delete([container["objectName"]] + members)

        return True


class MayaSelectInvalidInstanceAction(SelectInvalidInstanceAction):

    def select(self, invalid):
        from maya import cmds
        cmds.select(invalid, replace=True, noExpand=True)

    def deselect(self):
        from maya import cmds
        cmds.select(deselect=True)


class MayaSelectInvalidContextAction(SelectInvalidContextAction):
    """ Select invalid nodes in context"""

    def select(self, invalid):
        from maya import cmds
        cmds.select(invalid, replace=True, noExpand=True)

    def deselect(self):
        from maya import cmds
        cmds.select(deselect=True)
