
import os
import pyblish.api
import reveries.utils

from avalon.vendor import clique
from reveries.maya import io
from reveries.plugins import DelegatablePackageExtractor, skip_stage


class ExtractPlayblast(DelegatablePackageExtractor):
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

    @skip_stage
    def extract_imageSequence(self):
        """Extract playblast sequence directly to publish dir
        """

        start_frame = self.context.data["startFrame"]
        end_frame = self.context.data["endFrame"]

        entry_file = self.file_name(self.ext)
        publish_dir = self.create_package(entry_file)
        entry_path = os.path.join(publish_dir, entry_file)

        project = self.context.data["projectDoc"]
        width, height = reveries.utils.get_resolution_data(project)

        camera = self.data["renderCam"][0]
        io.capture_seq(camera,
                       entry_path,
                       start_frame,
                       end_frame,
                       width,
                       height)

        # Check image sequence length to ensure that the extraction did
        # not interrupted.
        files = os.listdir(publish_dir)
        # (NOTE) Did not consider frame step (byFrame)
        length = end_frame - start_frame + 1
        collections, _ = clique.assemble(files, minimum_items=length)

        assert (len(collections) == 1,
                "Extraction failed, possible insufficient sequence length.")

        sequence = collections[0]

        assert (len(sequence.indexes) == length,
                "Sequence length not match, this is a bug.")

        entry_fname = (sequence.head +
                       "%%0%dd" % sequence.padding +
                       sequence.tail)

        self.add_data({
            "imageFormat": self.ext,
            "entry_fname": entry_fname,
            "seqStart": list(sequence.indexes)[0],
            "seqEnd": list(sequence.indexes)[-1],
            "startFrame": start_frame,
            "endFrame": end_frame,
            "byFrameStep": 1,
            "renderlayer": self.data["renderlayer"],
        })
