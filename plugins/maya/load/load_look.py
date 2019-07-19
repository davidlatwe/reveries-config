
import os
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

        expanded = os.path.expandvars(entry_path).replace("\\", "/")
        loaded = expanded in cmds.file(query=True, reference=True)
        overload = options.get("overload")

        if not loaded or overload:

            if loaded and overload:
                self.log.info("Loading lookdev again..")
            else:
                self.log.info("Loading lookdev for the first time..")

            nodes = cmds.file(
                entry_path,
                namespace=namespace,
                ignoreVersion=True,
                reference=True,
                returnNewNodes=True
            )

        else:
            self.log.warning("Already Existed in scene.")
            return

        self[:] = nodes

    def update(self, container, representation):
        """Update look assignment

        Before update reference, assign back to `lambert1`, then reassign to
        the updated look. This could prevent shader lost when the shadingEngine
        node name changed in other version.

        """
        from maya import cmds
        from reveries.maya import lib
        from avalon.maya.pipeline import AVALON_CONTAINER_ID, parse_container

        nodes = cmds.sets(container["objectName"], query=True)
        shaders = cmds.ls(nodes, type="shadingEngine")
        shaded = cmds.ls(cmds.sets(shaders, query=True), long=True)

        # Collect current reference's placeholder connections
        reference_node = self.get_reference_node(container)
        placeholder_attr = reference_node + ".placeHolderList"
        placeholder_conns = cmds.listConnections(placeholder_attr,
                                                 source=True,
                                                 destination=False,
                                                 plugs=True,
                                                 connections=True,
                                                 shapes=True,
                                                 type="surfaceShape") or []
        placeholder_map = {
            cmds.ls(src.split(".", 1), long=True)[0]: (src, dst)
            for src, dst in
            zip(placeholder_conns[1::2], placeholder_conns[::2])
        }

        shader_missing_nodes = set(placeholder_map.keys())
        shader_missing_fixes = list()

        # Find shaded subsets from nodes
        shaded_subsets = list()

        shaded_nodes = set(cmds.ls(shaded, objectsOnly=True, long=True))
        containers = {
            con: set(cmds.ls(cmds.sets(con, query=True), long=True))
            for con in lib.lsAttrs({"id": AVALON_CONTAINER_ID})
            if not cmds.getAttr(con + ".loader") == "LookLoader"
        }
        for con, content in containers.items():
            if shaded_nodes.intersection(content):
                shaded_subsets.append(con)

                for node in shader_missing_nodes.intersection(content):
                    shader_missing_fixes.append(placeholder_map[node])

        # Fix if missing
        if shader_missing_fixes:
            # Remove placeholder connections so the shader assignment
            # could update properly.
            self.log.warning("Reference placeholder connection found, "
                             "possible shader connection missing from "
                             "previous geometry update.")
            self.log.warning("Performing auto fix..")

            for src, dst in shader_missing_fixes:
                if cmds.isConnected(src, dst):
                    cmds.disconnectAttr(src, dst)

        # Assign to lambert1
        self.log.info("Fallback to lambert1..")
        lib.force_element(shaded, "initialShadingGroup")

        # Container node name may changed after update
        uuid = cmds.ls(container["objectName"], uuid=True)

        # Update
        super(LookLoader, self).update(container, representation)

        if not shaded_subsets:
            self.log.warning("Version updated, but shader has no assignment.")
            return

        # Updated container data and re-assign shaders
        container = parse_container(cmds.ls(uuid)[0])
        self._assign_shaders(representation, container, shaded_subsets)

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

    def _assign_shaders(self, representation, container, containers):
        """Assign shaders to containers
        """
        import os
        from reveries.maya.tools.mayalookassigner import commands
        from maya import cmds

        file_name = representation["data"]["linkFname"]
        relationship = os.path.join(self.package_path, file_name)

        if not os.path.isfile(relationship):
            self.log.warning("Look development asset "
                             "has no relationship data.\n"
                             "{!r} was not found".format(relationship))
            return

        # Apply shader to target subset by namespace
        target_namespaces = [cmds.getAttr(con + ".namespace") + ":"
                             for con in containers]

        commands.assign_look(target_namespaces, container, via_uv=False)
