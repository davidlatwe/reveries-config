
from . import PendableLoader, loader_error_box


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


class ReferenceLoader(PendableLoader):
    """A basic ReferenceLoader for Maya

    This will implement the basic behavior for a loader to inherit from that
    will containerize the reference and will implement the `remove` and
    `update` logic.

    """
    def process_reference(self, context, name, namespace, data):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def pendable_load(self, context, name=None, namespace=None, data=None):
        from avalon.maya import lib
        from avalon.maya.pipeline import containerise

        load_plugin(context["representation"]["name"])

        asset = context['asset']

        namespace = namespace or lib.unique_namespace(
            asset["name"] + "_",
            prefix="_" if asset["name"][0].isdigit() else "",
            suffix="_",
        )

        self.process_reference(context=context,
                               name=name,
                               namespace=namespace,
                               data=data)

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        if not nodes:
            return

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def pendable_update(self, container, representation):
        import os
        from maya import cmds

        load_plugin(representation["name"])

        file_type = representation["name"]
        if file_type == "FBXCache":
            file_type == "FBX"

        node = container["objectName"]

        # Assume asset has been referenced
        reference_node = next((node for node in cmds.sets(node, query=True)
                               if cmds.nodeType(node) == "reference"), None)

        if not reference_node:
            title = "Update Abort"
            message = ("Imported container not supported; container must be "
                       "referenced.")
            loader_error_box(title, message)
            return

        path = self.entry_path
        assert os.path.exists(path), "%s does not exist." % path
        cmds.file(path, loadReference=reference_node, type=file_type)

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
            loader_error_box(title, message)
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


class ImportLoader(PendableLoader):

    def process_import(self, context, name, namespace, data):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def pendable_load(self, context, name=None, namespace=None, data=None):
        from avalon.maya import lib
        from avalon.maya.pipeline import containerise

        load_plugin(context["representation"]["name"])

        asset = context['asset']

        namespace = namespace or lib.unique_namespace(
            asset["name"] + "_",
            prefix="_" if asset["name"][0].isdigit() else "",
            suffix="_",
        )

        self.process_import(context=context,
                            name=name,
                            namespace=namespace,
                            data=data)

        # Only containerize if any nodes were loaded by the Loader
        nodes = self[:]
        if not nodes:
            return

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def pendable_update(self, container, representation):

        title = "Can Not Update"
        message = ("The content of this asset was imported. "
                   "We cannot update this because we will need"
                   " to keep insane amount of things in mind.\n"
                   "Please remove and reimport the asset."
                   "\n\nIf you really need to update a lot we "
                   "recommend referencing.")

        loader_error_box(title, message)
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
