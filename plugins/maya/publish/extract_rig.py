
import contextlib
import pyblish.api


class ExtractRig(pyblish.api.InstancePlugin):
    """Extract rig as mayaBinary"""

    label = "Extract Rig (mb)"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.rig"]

    def process(self, instance):
        from maya import cmds
        from avalon import maya
        from reveries import utils
        from reveries.maya import capsule

        staging_dir = utils.stage_dir()
        filename = "%s.mb" % instance.data["subset"]
        outpath = "%s/%s" % (staging_dir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")
        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_display_layers(instance[:]),
            maya.maintained_selection(),
        ):
            with capsule.undo_chunk_when_no_undo():

                """(DEPRECATED, keeping namespaces)
                # - Remove referenced subset's namespace before exporting
                #   (Not keeping model namespace)
                referenced_namespace = self.context.data["referencedNamespace"]
                for namespace in reversed(sorted(list(referenced_namespace))):
                    if not cmds.namespace(exists=namespace):
                        continue

                    try:
                        cmds.namespace(removeNamespace=namespace,
                                       mergeNamespaceWithRoot=True)
                    except Exception:
                        # Reload reference and try again.
                        # The namespace of the reference will be able to
                        # removed after reload.
                        # (TODO) This publish workflow might not be a good
                        #        approach...
                        ref_node = lib.reference_node_by_namespace(namespace)
                        # There must be a reference node, since that's the
                        # main reason why namespace can not be removed.
                        cmds.file(loadReference=ref_node)
                        cmds.namespace(removeNamespace=namespace,
                                       mergeNamespaceWithRoot=True)
                """

                # - Remove loaded container member
                #   If the mesh of the loaded model has been copied and edited
                #   (mesh face detach and separation), the model container
                #   might end up with a lots of facet member, which means there
                #   are dag connections that would make the model container be
                #   exported as well, and we don't want that happens.
                #   So we just remove them all for good.
                for container in instance.context.data["RootContainers"]:
                    cmds.delete(container)

                mesh_nodes = cmds.ls(instance,
                                     type="mesh",
                                     noIntermediate=True,
                                     long=True)
                geo_id_and_hash = self.hash(set(mesh_nodes))

                cmds.select(cmds.ls(instance), noExpand=True)

                cmds.file(outpath,
                          force=True,
                          typ="mayaBinary",
                          exportSelected=True,
                          preserveReferences=False,
                          channels=True,
                          constraints=True,
                          expressions=True,
                          constructionHistory=True,
                          shader=True)

        instance.data["repr.mayaBinary._stage"] = staging_dir
        instance.data["repr.mayaBinary._files"] = [filename]
        instance.data["repr.mayaBinary.entryFileName"] = filename
        instance.data["repr.mayaBinary.modelProfile"] = geo_id_and_hash

    def hash(self, mesh_nodes):
        from maya import cmds
        from reveries.maya import utils as maya_utils

        # Hash model and collect Avalon UUID
        geo_id_and_hash = dict()
        hasher = maya_utils.MeshHasher()
        for mesh in mesh_nodes:
            # Get ID
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
            id = maya_utils.get_id(transform)
            assert id is not None, ("Some mesh has no Avalon UUID. "
                                    "This should not happend.")
            hasher.set_mesh(mesh)
            hasher.update_points()
            hasher.update_normals()
            hasher.update_uvmap()

            result = hasher.digest()
            result["hierarchy"] = transform

            # May have duplicated Id
            if id not in geo_id_and_hash:
                geo_id_and_hash[id] = list()
            geo_id_and_hash[id].append(result)

            hasher.clear()

        return geo_id_and_hash
