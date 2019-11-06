
import contextlib
import avalon.api
import avalon.maya

from reveries import utils
from reveries.maya import pipeline
from reveries.maya.plugins import ReferenceLoader


class RigLoader(ReferenceLoader, avalon.api.Loader):
    """Specific loader for rigs

    This automatically creates an instance for animators upon load.

    """
    label = "Reference rig"
    order = -10
    icon = "code-fork"
    color = "orange"

    hosts = ["maya"]

    families = ["reveries.rig"]

    representations = [
        "mayaBinary",
    ]

    def process_reference(self, context, name, namespace, group, options):

        import maya.cmds as cmds

        representation = context["representation"]

        entry_path = self.file_path(representation)

        nodes = cmds.file(entry_path,
                          namespace=namespace,
                          ignoreVersion=True,
                          reference=True,
                          returnNewNodes=True,
                          groupReference=True,
                          groupName=group)

        self[:] = nodes

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        from maya import cmds

        node = container["objectName"]

        # Get reference node from container
        reference_node = self.get_reference_node(container)

        with patch(reference_node):

            parents = avalon.io.parenthood(representation)
            self.package_path = utils.get_representation_path_(representation,
                                                               parents)
            entry_path = self.file_path(representation)
            self.log.info("Reloading reference from: {!r}".format(entry_path))

            cmds.file(entry_path,
                      loadReference=reference_node,
                      type="mayaBinary",
                      defaultExtensions=False)

            # Add new nodes of the reference to the container
            nodes = cmds.referenceQuery(reference_node,
                                        nodes=True,
                                        dagPath=True)

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
            pipeline.update_container(container,
                                      asset,
                                      subset,
                                      version,
                                      representation)


@contextlib.contextmanager
def patch(reference_node):
    """A patch after commit 06c2ef9 and should be removed ASAP

    Before commit 06c2ef9, published rig has no namespace on imported
    models or shaders.

    And sometimes animator may make their own change on referenced rig
    that may create extra meshes under referenced transform node, which
    Maya will not able to re-apply those edits when replacing reference
    if the original rig was published before commit 06c2ef9 and the new
    rig was published after that (because new node will have namespace).

    Hence we need this patch for the transition, and will remove this once
    we could pin config version on each project.

    """
    from maya import cmds

    referenced = cmds.referenceQuery(reference_node,
                                     nodes=True,
                                     dagPath=True)
    transforms = cmds.ls(referenced, type="transform", long=True)
    meshes = cmds.listRelatives(transforms,
                                shapes=True,
                                fullPath=True,
                                type="mesh") or []

    # Collect meshes(uuid) that were created in scene

    mesh_uuids = dict()
    for mesh in meshes:
        if cmds.referenceQuery(mesh, isNodeReferenced=True):
            continue

        parent = cmds.ls(mesh.rsplit("|", 1)[0], uuid=True)[0]
        shading = cmds.ls(cmds.listConnections(mesh,
                                               source=False,
                                               destination=True,
                                               connections=True,
                                               type="shadingEngine"),
                          uuid=True)
        mesh = cmds.ls(mesh, uuid=True)[0]
        mesh_uuids[mesh] = (parent, shading)

    yield

    # Adopt new parent

    foster = cmds.listConnections(reference_node + ".fosterParent")
    if foster and mesh_uuids:
        foster = foster[0]

        shapes = cmds.listRelatives(foster, shapes=True, fullPath=True)
        shapes = cmds.ls(shapes, uuid=True)
        for uuid in shapes:
            if uuid not in mesh_uuids:
                continue

            parent, shading = mesh_uuids[uuid]
            parent = cmds.ls(parent)
            fostered_shape = cmds.ls(uuid, long=True)

            if parent and fostered_shape:
                # Move fostered mesh node to newly referenced transform node
                fostered_shape = fostered_shape[0]
                shape = cmds.parent(fostered_shape,
                                    parent[0],
                                    addObject=True,
                                    shape=True)
                cmds.parent(fostered_shape,
                            removeObject=True,
                            shape=True)

                # Try to fix shading
                if shading:
                    shading = iter(shading)
                    for src, dst in zip(shading, shading):
                        dst = cmds.ls(dst)
                        if not dst:
                            continue
                        src = shape[0] + "." + src.split(".", 1)[-1]
                        dst = dst[0] + ".dagSetMembers"

                        try:
                            cmds.connectAttr(src, dst, nextAvailable=True)
                        except Exception as e:
                            cmds.warning(str(e))
