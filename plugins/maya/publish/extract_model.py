
import os
import contextlib
import pyblish.api

import maya.cmds as cmds
import avalon.maya as maya

from reveries.maya import capsule, io
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
        mesh_nodes = cmds.ls(self.member, type='mesh', ni=True, long=True)
        clay_shader = "initialShadingGroup"

        with contextlib.nested(
            capsule.no_undo(),
            capsule.no_display_layers(self.member),
            capsule.no_smooth_preview(),
            capsule.assign_shader(mesh_nodes, shadingEngine=clay_shader),
            maya.maintained_selection(),
            maya.without_extension(),
        ):
            super(ExtractModel, self).extract()

    def extract_mayaBinary(self):
        entry_file = self.file_name("ma")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)

        # Perform extraction
        self.log.info("Extracting %s" % str(self.member))
        cmds.select(self.member, noExpand=True)
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

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=entry_path)
        )

    def extract_GPUCache(self):
        entry_file = self.file_name("abc")
        package_path = self.create_package(entry_file)
        entry_path = os.path.join(package_path, entry_file)
        frame = cmds.currentTime(query=True)
        io.export_gpu(entry_path, frame, frame)
