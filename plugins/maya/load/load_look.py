
import avalon.api
from reveries.maya.plugins import ReferenceLoader


class LookLoader(ReferenceLoader, avalon.api.Loader):
    """Specific loader for lookdev"""

    label = "Reference look"
    order = -10
    icon = "code-fork"
    color = "orange"

    hosts = ["maya"]

    families = ["reveries.look"]

    representations = [
        "LookDev",
    ]

    def process_reference(self, context, name, namespace, group, options):
        from maya import cmds

        representation = context["representation"]

        entry_path = self.file_path(representation["data"]["entry_fname"])

        try:
            existing_reference = cmds.file(entry_path,
                                           query=True,
                                           referenceNode=True)
        except RuntimeError as e:
            if e.message.rstrip() != "Cannot find the scene file.":
                raise

            self.log.info("Loading lookdev for the first time..")
            nodes = cmds.file(
                entry_path,
                namespace=namespace,
                reference=True,
                returnNewNodes=True
            )
        else:
            self.log.info("Reusing existing lookdev..")
            nodes = cmds.referenceQuery(existing_reference, nodes=True)
            namespace = nodes[0].split(":", 1)[0]

        # Assign shaders
        self._assign_shaders(representation, namespace)

        self[:] = nodes

        self.interface = cmds.ls(nodes, type="shadingEngine")

    def update(self, container, representation):
        from maya import cmds

        # Assign to lambert1
        nodes = cmds.sets(container["objectName"], query=True)
        shaders = cmds.ls(nodes, type="shadingEngine")
        shaded = cmds.ls(cmds.sets(shaders, query=True), long=True)
        cmds.sets(shaded, forceElement="initialShadingGroup")

        # Update
        super(LookLoader, self).update(container, representation)

        # Reassign shaders
        namespace = container["namespace"][1:]
        self._assign_shaders(representation, namespace)

    def remove(self, container):
        from maya import cmds

        # Query assigned object
        nodes = cmds.sets(container["objectName"], query=True)
        shaders = cmds.ls(nodes, type="shadingEngine")
        shaded = cmds.ls(cmds.sets(shaders, query=True), long=True)

        # Remove
        if not super(LookLoader, self).remove(container):
            return

        # Assign to lambert1
        cmds.sets(shaded, forceElement="initialShadingGroup")

        return True

    def _assign_shaders(self, representation, namespace):
        import os
        import json
        from reveries.maya import lib, plugins

        relationship = self.file_path(representation["data"]["link_fname"])
        # Expand $AVALON_PROJECT and friends, if used
        relationship = os.path.expandvars(relationship)

        if not os.path.isfile(relationship):
            self.log.warning("Look development asset "
                             "has no relationship data.\n"
                             "{!r} was not found".format(relationship))
            return

        # Load map
        with open(relationship) as f:
            relationships = json.load(f)

        # Apply shader to target subset by namespace
        target_namespaces = list()
        target_subset = representation["data"]["target_subset"]

        interfaces = lib.lsAttrs({
            "id": plugins.AVALON_CONTAINER_INTERFACE_ID,
            "subsetId": target_subset})
        for interface in interfaces:
            target_namespaces.append(
                plugins.parse_interface(interface)["namespace"] + ":"
            )

        lib.apply_shaders(relationships["shader_by_id"],
                          namespace,
                          target_namespaces)
