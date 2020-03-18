
import os
import contextlib
import pyblish.api

from maya import cmds
from avalon import maya

from reveries.plugins import PackageExtractor
from reveries.maya import capsule, utils


class ExtractRig(PackageExtractor):
    """Extract rig as mayaBinary"""

    label = "Extract Rig (mayaBinary)"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.rig"]

    representations = [
        "mayaBinary",
    ]

    def extract_mayaBinary(self, instance):
        # Define extract output file path
        packager = instance.data["packager"]
        package_path = packager.create_package()

        entry_file = packager.file_name("mb")
        entry_path = os.path.join(package_path, entry_file)

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
                packager.add_data({"modelProfile": geo_id_and_hash})

                cmds.select(cmds.ls(instance), noExpand=True)

                cmds.file(entry_path,
                          force=True,
                          typ="mayaBinary",
                          exportSelected=True,
                          preserveReferences=False,
                          channels=True,
                          constraints=True,
                          expressions=True,
                          constructionHistory=True,
                          shader=True)

        packager.add_data({
            "entryFileName": entry_file,
        })

        self.log.info("Extracted {name} to {path}".format(
            name=instance.data["subset"],
            path=entry_path)
        )

    def hash(self, mesh_nodes):
        # Hash model and collect Avalon UUID
        geo_id_and_hash = dict()
        hasher = utils.MeshHasher()
        for mesh in mesh_nodes:
            # Get ID
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
            id = utils.get_id(transform)
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
