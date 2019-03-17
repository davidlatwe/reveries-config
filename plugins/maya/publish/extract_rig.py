
import os
import contextlib
import pyblish.api

from maya import cmds
from avalon import maya

from reveries.plugins import PackageExtractor
from reveries.maya import capsule, lib, utils


class ExtractRig(PackageExtractor):
    """Extract rig as mayaBinary"""

    label = "Extract Rig (mayaBinary)"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    families = ["reveries.rig"]

    representations = [
        "mayaBinary",
    ]

    def extract_mayaBinary(self):
        # Define extract output file path
        entry_file = self.file_name("mb")
        package_path = self.create_package()
        entry_path = os.path.join(package_path, entry_file)

        mesh_nodes = cmds.ls(self.member,
                             type="surfaceShape",
                             noIntermediate=True,
                             long=True)
        clay_shader = "initialShadingGroup"

        # Hash model and collect Avalon UUID
        geo_id_and_hash = dict()
        hasher = utils.MeshHasher()
        for mesh in mesh_nodes:
            # Get ID
            transform = cmds.listRelatives(mesh, parent=True, fullPath=True)[0]
            id = utils.get_id(transform)
            hasher.set_mesh(mesh)
            hasher.update_points()
            hasher.update_normals()
            hasher.update_uvmap()
            # It must be one mesh paring to one transform.
            geo_id_and_hash[id] = hasher.digest()
            hasher.clear()

        self.add_data({"modelProfile": geo_id_and_hash})

        # Perform extraction
        self.log.info("Performing extraction..")
        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_display_layers(self.member),
            maya.maintained_selection(),
            capsule.assign_shader(mesh_nodes, shadingEngine=clay_shader),
        ):
            with capsule.undo_chunk_when_no_undo():
                # (NOTE) Current workflow may keep model stay loaded as
                #   referenced in scene, but need to take extra care while
                #   extracting. (Will be undone)

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

                # - Remove loaded container member
                #   If the mesh of the loaded model has been copied and edited
                #   (mesh face detach and separation), the model container
                #   might end up with a lots of facet member, which means there
                #   are dag connections that would make the model container be
                #   exported as well, and we don't want that happens.
                #   So we just remove them all for good.
                for container in self.context.data["RootContainers"]:
                    cmds.delete(container)

                cmds.select(cmds.ls(self.member), noExpand=True)

                cmds.file(entry_path,
                          force=True,
                          typ="mayaBinary",
                          exportSelected=True,
                          preserveReferences=False,
                          channels=True,
                          constraints=True,
                          expressions=True,
                          constructionHistory=True)

        self.add_data({
            "entryFileName": entry_file,
        })

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=entry_path)
        )
