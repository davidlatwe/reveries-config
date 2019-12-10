
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
        from reveries.maya import lib
        from avalon.maya.pipeline import AVALON_CONTAINER_ID

        representation = context["representation"]

        entry_path = self.file_path(representation)

        expanded = os.path.expandvars(entry_path).replace("\\", "/")
        loaded = expanded in cmds.file(query=True, reference=True)
        overload = options.get("overload")

        if loaded:
            # Has been referenced, but is it containerized ?
            id = str(representation["_id"])
            loaded = bool(lib.lsAttrs({"id": AVALON_CONTAINER_ID,
                                       "loader": "LookLoader",
                                       "representation": id}))
            if not loaded:
                self.log.warning("Look has been referenced, but not "
                                 "containerized.., will load a new one.")

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
            reference = cmds.referenceQuery(expanded, referenceNode=True)
            self.log.warning("Already referenced in scene: %s" % reference)
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

        # Flag `_preserveRefEdit` from `container` is a workaround
        # should coming from `options`
        preserve_edit = container.pop("_preserveRefEdit", False)

        nodes = cmds.sets(container["objectName"], query=True)
        shaders = cmds.ls(nodes, type="shadingEngine")
        shaded = cmds.ls(cmds.sets(shaders, query=True))

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
            cmds.ls(src.split(".", 1))[0]: (src, dst)
            for src, dst in
            zip(placeholder_conns[1::2], placeholder_conns[::2])
        }

        shader_missing_nodes = set(placeholder_map.keys())
        shader_missing_fixes = list()

        contents = [
            set(cmds.ls(cmds.sets(con, query=True)))
            for con in lib.lsAttrs({"id": AVALON_CONTAINER_ID})
            if not cmds.getAttr(con + ".loader") == "LookLoader"
        ]
        for content in contents:
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
        if not preserve_edit:
            container["_dropRefEdit"] = True
        super(LookLoader, self).update(container, representation)

        shaded_nodes = set(cmds.ls(shaded, objectsOnly=True))
        if not shaded_nodes:
            self.log.warning("Version updated, but shader has no assignment.")
            return

        # Updated container data and re-assign shaders
        container = parse_container(cmds.ls(uuid)[0])
        nodes = cmds.listRelatives(list(shaded_nodes), parent=True, path=True)
        self._assign_shaders(representation, container, nodes)

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

    def _assign_shaders(self, representation, container, nodes):
        """Assign shaders to containers
        """
        import os
        from reveries.maya.tools.mayalookassigner import commands

        file_name = representation["data"]["linkFname"]
        relationship = os.path.join(self.package_path, file_name)

        if not os.path.isfile(relationship):
            self.log.warning("Look development asset "
                             "has no relationship data.\n"
                             "{!r} was not found".format(relationship))
            return

        # Apply shader
        commands.assign_look(nodes, container, via_uv=False)
