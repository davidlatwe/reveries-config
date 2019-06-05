
import avalon.api


class UnpackLoadedSubset(avalon.api.InventoryAction):
    """Unpack loaded subset into scene
    """

    label = "Unpack Subset"
    icon = "warning"
    color = "#ff6666"
    order = 200

    @staticmethod
    def is_compatible(container):
        from maya import cmds
        from avalon.maya.pipeline import AVALON_CONTAINERS

        if not container:
            return False

        if container["loader"] not in [
            "CameraLoader",
            "LightSetLoader",
            "LookLoader",
            "MayaShareLoader",
            "ModelLoader",
            "PointCacheReferenceLoader",
            "RigLoader",
            "SetDressLoader",
        ]:
            return False

        containers = AVALON_CONTAINERS[1:]  # Remove root namespace
        parents = cmds.listSets(object=container["objectName"]) or []
        # Must be a root container
        if containers in parents:
            return True
        return False

    def consent(self):
        from reveries.plugins import message_box_warning

        title = "Unpack Subset"
        msg = ("Subset will not be able to update nor managed after "
               "this action.\nAre you sure ?")

        return message_box_warning(title, msg, optional=True)

    def _get_reference_node(self, members):
        """Get the reference node from the container members
        Args:
            members: list of node names

        Returns:
            str: Reference node name.

        """
        from reveries.maya import lib

        # Collect the references without .placeHolderList[] attributes as
        # unique entries (objects only) and skipping the sharedReferenceNode.
        references = lib.get_reference_node(members)

        if not references:
            return None

        # Get highest reference node (least parents)
        highest = lib.get_highest_reference_node(references)

        return highest

    def process(self, containers):
        from maya import cmds
        from avalon.maya.pipeline import AVALON_CONTAINERS
        from avalon.tools import cbsceneinventory
        from reveries.maya import hierarchy, pipeline
        from reveries.maya.vendor import sticker
        from reveries import REVERIES_ICONS

        if not self.consent():
            return

        dimmed_icon = REVERIES_ICONS + "/package-01-dimmed.png"

        for container in containers:
            if not self.is_compatible(container):
                continue

            node = container["objectName"]
            members = cmds.sets(node, query=True) or []

            reference_node = self._get_reference_node(members)
            if reference_node is not None:
                # Import Reference
                cmds.file(importReference=True, referenceNode=reference_node)

            namespace = container["namespace"]

            for child in hierarchy.get_sub_container_nodes(container):
                # Update sub-containers' namespace entry
                child_ns = cmds.getAttr(child + ".namespace")
                new_ns = child_ns[len(namespace):]
                cmds.setAttr(child + ".namespace", new_ns, type="string")
                # Add to root container
                cmds.sets(child, forceElement=AVALON_CONTAINERS)

            # Merge namespace to root
            cmds.namespace(removeNamespace=namespace,
                           mergeNamespaceWithRoot=True)

            # Update subset group icon
            group = pipeline.get_group_from_container(node)
            if group is not None:
                sticker.put(group, dimmed_icon)

            # Delete container
            cmds.delete(node)

        # Refresh GUI
        cbsceneinventory.app.window.refresh()

        # Update Icon
        sticker.reveal()
