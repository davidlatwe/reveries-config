
import os
import contextlib
import pyblish.api
import reveries.utils
import reveries.base
import reveries.maya.capsule as capsule
import maya.cmds as cmds
import avalon.maya as maya


class ExtractModel(reveries.base.BaseExtractor):
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
        reveries.base.repr_obj("mayaBinary", "mb")
    ]

    def dispatch(self):
        mesh_nodes = cmds.ls(self.member, type='mesh', ni=True, long=True)
        clay_shader = "initialShadingGroup"

        with contextlib.nested(
            capsule.no_display_layers(self.member),
            capsule.no_smooth_preview(),
            capsule.assign_shader(mesh_nodes, shadingEngine=clay_shader),
            maya.maintained_selection(),
            maya.without_extension(),
        ):
            self.extract()

    def extract_mayaBinary(self, representation):
        dirname = self.extraction_dir(representation)
        filename = self.extraction_fname(representation)

        out_path = os.path.join(dirname, filename)
        # Perform extraction
        self.log.info("Extracting %s" % str(self.member))
        cmds.select(self.member, noExpand=True)
        cmds.file(
            out_path,
            force=True,
            typ=representation,
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

        self.stage_files(representation)

        self.log.info("Extracted {name} to {path}".format(
            name=self.data["subset"],
            path=out_path)
        )
