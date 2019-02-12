
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

        entry_path = self.file_path(representation)

        if entry_path in cmds.file(query=True, reference=True):

            existing_reference = cmds.file(entry_path,
                                           query=True,
                                           referenceNode=True)

            self.log.info("Reusing existing lookdev..")
            nodes = cmds.referenceQuery(existing_reference, nodes=True)
            namespace = nodes[0].split(":", 1)[0]

        else:
            self.log.info("Loading lookdev for the first time..")
            nodes = cmds.file(
                entry_path,
                namespace=namespace,
                ignoreVersion=True,
                reference=True,
                returnNewNodes=True
            )

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
        import avalon.maya
        from reveries.maya import lib

        file_name = representation["data"]["linkFname"]
        relationship = os.path.join(self.package_path, file_name)

        if not os.path.isfile(relationship):
            self.log.warning("Look development asset "
                             "has no relationship data.\n"
                             "{!r} was not found".format(relationship))
            return

        # Load map
        with open(relationship) as f:
            relationships = json.load(f)

        # Apply shader to target subset by namespace
        targets = [str(tg) for tg in representation["data"]["targetSubsets"]]
        target_namespaces = [con["namespace"] + ":" for con in avalon.maya.ls()
                             if con["subsetId"] in targets]

        lib.apply_shaders(relationships["shaderById"],
                          namespace,
                          target_namespaces)
