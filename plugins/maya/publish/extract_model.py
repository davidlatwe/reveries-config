
import os
import contextlib
import pyblish.api

import maya.cmds as cmds
import avalon.maya as maya

from reveries.maya import capsule, io, utils
from reveries.plugins import PackageExtractor


class ExtractModel(PackageExtractor):
    """Produce a stripped down Maya file from instance

    This plug-in takes into account only nodes relevant to models
    and discards anything else, especially deformers along with
    their intermediate nodes.

    """

    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]
    label = "Extract Model"
    families = ["reveries.model"]

    representations = [
        "mayaBinary",
        "GPUCache",
    ]

    def extract(self):

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_display_layers(self.member),
            capsule.no_smooth_preview(),
            maya.maintained_selection(),
            maya.without_extension(),
        ):
            super(ExtractModel, self).extract()

    def extract_mayaBinary(self):
        entry_file = self.file_name("mb")
        package_path = self.create_package()
        entry_path = os.path.join(package_path, entry_file)

        mesh_nodes = cmds.ls(self.member,
                             type="mesh",
                             noIntermediate=True,
                             long=True)
        clay_shader = "initialShadingGroup"

        # Hash model
        hasher = utils.MeshHasher()
        for mesh in mesh_nodes:
            hasher.set_mesh(mesh)
            hasher.update_points()
            hasher.update_normals()
            hasher.update_uvmap()

        self.add_data({"meshHash": hasher.digest()})

        # Perform extraction
        self.log.info("Extracting %s" % str(self.member))
        cmds.select(self.member, noExpand=True)

        with contextlib.nested(
            capsule.assign_shader(mesh_nodes, shadingEngine=clay_shader),
            capsule.undo_chunk_when_no_undo(),
        ):
            # Remove mesh history, for removing all intermediate nodes
            transforms = cmds.ls(self.member, type="transform")
            cmds.delete(transforms, constructionHistory=True)
            # Remove all stray shapes, ensure no intermediate nodes
            all_meshes = set(cmds.ls(self.member, type="mesh", long=True))
            cmds.delete(list(all_meshes - set(mesh_nodes)))

            cmds.file(
                entry_path,
                force=True,
                typ="mayaBinary",
                exportSelected=True,
                preserveReferences=False,
                # Shader assignment is the responsibility of
                # riggers, for animators, and lookdev, for
                # rendering.
                shader=False,
                # Construction history inherited from collection
                # This enables a selective export of nodes
                # relevant to this particular plug-in.
                constructionHistory=False
            )

        self.add_data({
            "entryFileName": entry_file,
        })

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=entry_path)
        )

    def extract_GPUCache(self):
        entry_file = self.file_name("ma")
        cache_file = self.file_name("abc")
        package_path = self.create_package()
        entry_path = os.path.join(package_path, entry_file)
        cache_path = os.path.join(package_path, cache_file)

        frame = cmds.currentTime(query=True)
        io.export_gpu(cache_path, frame, frame)
        io.wrap_gpu(entry_path, [(cache_file, self.data["subset"])])

        self.add_data({
            "entryFileName": entry_file,
        })
