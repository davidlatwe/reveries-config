
import os
import json

import avalon.api
import avalon.io
import avalon.maya

from .utils import (
    update_id_on_import,
    generate_container_id,
)

from ..utils import get_representation_path_

from ..plugins import (
    PackageLoader,
    message_box_error,
    SelectInvalidAction,
    SelectInvalidContextAction,
)

from .pipeline import (
    subset_group_name,
    subset_containerising,
    unique_root_namespace,
    update_container,
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


class MayaBaseLoader(PackageLoader):

    interface = []

    def file_path(self, representation):
        file_name = representation["data"]["entryFileName"]
        entry_path = os.path.join(self.package_path, file_name)

        if not os.path.isfile(entry_path):
            raise IOError("File Not Found: {!r}".format(entry_path))

        return env_embedded_path(entry_path)

    def group_name(self, namespace, name):
        return subset_group_name(namespace, name)


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

        load_plugin(context["representation"]["name"])

        asset = context["asset"]

        asset_name = asset["data"].get("shortName", asset["name"])
        family_name = context["version"]["data"]["families"][0].split(".")[-1]
        namespace = namespace or unique_root_namespace(asset_name, family_name)

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

        container_id = options.get("containerId", generate_container_id())

        container = subset_containerising(name=name,
                                          namespace=namespace,
                                          container_id=container_id,
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
        elif file_type in ("GPUCache", "LookDev"):
            file_type = "MayaAscii"

        parents = avalon.io.parenthood(representation)
        self.package_path = get_representation_path_(representation, parents)

        entry_path = self.file_path(representation)

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
        update_container(container, asset, subset, version, representation)

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


class ImportLoader(MayaBaseLoader):

    def process_import(self, context, name, namespace, options):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def load(self, context, name=None, namespace=None, options=None):

        load_plugin(context["representation"]["name"])

        asset = context['asset']

        asset_name = asset["data"].get("shortName", asset["name"])
        family_name = context["version"]["data"]["families"][0].split(".")[-1]
        namespace = namespace or unique_root_namespace(asset_name, family_name)

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

        container_id = options.get("containerId", generate_container_id())

        container = subset_containerising(name=name,
                                          namespace=namespace,
                                          container_id=container_id,
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


class HierarchicalLoader(MayaBaseLoader):
    """Hierarchical referencing based asset loader
    """

    def _members_data_from_container(self, container):
        current_repr = avalon.io.find_one({
            "_id": avalon.io.ObjectId(container["representation"]),
            "type": "representation"
        })
        package_path = avalon.api.get_representation_path(current_repr)
        entry_file = self.file_path(current_repr)
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
        family_name = context["version"]["data"]["families"][0].split(".")[-1]
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

        update_id_on_import(hierarchy)

        # Load sub-subsets
        sub_containers = []
        sub_interfaces = []
        for data in members:

            repr_id = data["representation"]
            data["representationDoc"] = get_representation(repr_id)
            data["loaderCls"] = get_loader(data["loader"], repr_id)

            root = group_name
            with add_subset(data, namespace, root) as sub_container:

                self.apply_variation(data=data,
                                     container=sub_container)

            sub_containers.append(sub_container["objectName"])
            sub_interfaces.append(sub_container["interface"])

        self[:] = hierarchy + sub_containers
        self.interface = [group_name] + sub_interfaces

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        if not nodes:
            return

        container = subset_containerising(name=name,
                                          namespace=namespace,
                                          container_id=container_id,
                                          nodes=nodes,
                                          ports=self.interface,
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

        update_id_on_import(hierarchy)

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


class MayaSelectInvalidContextAction(SelectInvalidContextAction,
                                     MayaSelectInvalidAction):
    """ Select invalid nodes in context"""
