
import os
import pyblish.api
import reveries.utils

from avalon.vendor import clique
from reveries.maya import io, utils
# from reveries.plugins import DelegatablePackageExtractor
from reveries.plugins import PackageExtractor


class ExtractPlayblast(PackageExtractor):
    """
    """

    label = "Extract Playblast"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]

    families = [
        "reveries.imgseq.playblast",
    ]

    representations = [
        "imageSequence"
    ]

    ext = "png"

    def extract_imageSequence(self, packager):
        """Extract playblast sequence directly to publish dir
        """
        from maya import cmds
        cmds.editRenderLayerGlobals(currentRenderLayer="defaultRenderLayer")

        packager.skip_stage()

        project = self.context.data["projectDoc"]
        width, height = reveries.utils.get_resolution_data(project)
        e_in, e_out, handles, _ = reveries.utils.get_timeline_data(project)

        start_frame = self.context.data["startFrame"]
        end_frame = self.context.data["endFrame"]

        suffix = "." + self.data["asset"]
        entry_file = packager.file_name(suffix=suffix)
        publish_dir = packager.create_package()
        entry_path = os.path.join(publish_dir, entry_file)

        pipeline_data = self.context.data["projectDoc"]["data"]["pipeline"]
        use_lights = pipeline_data["maya"].get("playblastLights", "default")

        camera = self.data["renderCam"][0]
        io.capture_seq(camera,
                       entry_path,
                       start_frame,
                       end_frame,
                       width,
                       height,
                       display_lights=use_lights)

        # Check image sequence length to ensure that the extraction did
        # not interrupted.
        files = os.listdir(publish_dir)
        collections, _ = clique.assemble(files)

        assert len(collections), "Extraction failed, no sequence found."

        sequence = collections[0]

        entry_fname = (sequence.head +
                       "%%0%dd" % sequence.padding +
                       sequence.tail)

        packager.add_data({
            "imageFormat": self.ext,
            "entryFileName": entry_fname,
            "seqStart": list(sequence.indexes)[0],
            "seqEnd": list(sequence.indexes)[-1],
            "startFrame": start_frame,
            "endFrame": end_frame,
            "byFrameStep": 1,
            "edit_in": e_in,
            "edit_out": e_out,
            "handles": handles,
            "focalLength": cmds.getAttr(camera + ".focalLength"),
            "resolution": (width, height),
            "fps": self.context.data["fps"],
            "cameraUUID": utils.get_id(camera),
        })
