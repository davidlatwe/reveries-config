
import os
import pyblish.api

from avalon.vendor import clique
from reveries.plugins import DelegatablePackageExtractor, skip_stage


class ExtractRender(DelegatablePackageExtractor):
    """Start GUI rendering if not delegate to Deadline
    """

    label = "Extract Render"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]

    families = [
        "reveries.imgseq.batchrender",
        "reveries.imgseq.turntable",
    ]

    representations = [
        "imageSequence",
        "imageSequenceSet",
    ]

    @skip_stage
    def extract_imageSequence(self):
        """Extract per renderlayer that has no AOVs
        """
        if not self.context.data.get("contractorAccepted"):
            self.start_local_rendering()

        repr_dir = self.create_package(None)

        # Assume the rendering has been completed at this time being,
        # start to check and extract the rendering outputs
        aov_name = ""

        # Collect output path
        output_path = self.data["outputPaths"][aov_name]

        # Check image sequence length to ensure that the extraction did
        # not interrupted.
        seq_dir = os.path.dirname(output_path)
        self.add_sequence(seq_dir, aov_name, repr_dir)

    @skip_stage
    def extract_imageSequenceSet(self):
        """Extract per renderlayer that has AOVs
        """
        if not self.context.data.get("contractorAccepted"):
            self.start_local_rendering()

        repr_dir = self.create_package(None)

        # Assume the rendering has been completed at this time being,
        # start to check and extract the rendering outputs
        for aov_name, aov_path in self.data["outputPaths"].items():
            # Check image sequence length to ensure that the extraction did
            # not interrupted.
            seq_dir = os.path.dirname(aov_path)
            self.add_sequence(seq_dir, aov_name, repr_dir)

    def add_sequence(self, seq_dir, seq_name, repr_dir):
        """
        """
        self.log.debug("Collecting sequence from: %s" % seq_dir)
        files = os.listdir(seq_dir)

        # (NOTE) Did not consider frame step (byFrame)
        start_frame = self.data["startFrame"]
        end_frame = self.data["endFrame"]
        length = end_frame - start_frame + 1
        collections, _ = clique.assemble(files, minimum_items=length)

        assert len(collections) == 1, ("Extraction failed, possible "
                                       "insufficient sequence length.")

        sequence = collections[0]

        assert len(sequence.indexes) == length, ("Sequence length not match, "
                                                 "this is a bug.")

        entry_fname = (sequence.head +
                       "%%0%dd" % sequence.padding +
                       sequence.tail)

        self.add_data({"sequence": {
            seq_name: {
                "imageFormat": self.data["fileExt"],
                "entry_fname": entry_fname,
                "seqStart": list(sequence.indexes)[0],
                "seqEnd": list(sequence.indexes)[-1],
                "startFrame": start_frame,
                "endFrame": end_frame,
                "byFrameStep": self.data["byFrameStep"],
                "renderlayer": self.data["renderlayer"],
            }
        }})

        for file in files:
            src = seq_dir + "/" + file
            dst = os.path.join(repr_dir, seq_name, file)
            self.data["hardlinks"].append((src, dst))

    def start_local_rendering(self):
        """Start rendering at local with GUI
        """
        # reveries.maya.io.gui_rendering()
        raise NotImplementedError
