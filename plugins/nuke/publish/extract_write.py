
import os
import pyblish.api
import reveries.utils
import reveries.lib

from avalon.vendor import clique
from reveries.plugins import PackageExtractor


class ExtractWrite(PackageExtractor):
    """Start GUI rendering if not delegate to Deadline
    """

    label = "Extract Write"
    order = pyblish.api.ExtractorOrder
    hosts = ["nuke"]

    targets = ["localhost"]

    families = [
        "reveries.write",
    ]

    representations = [
        "imageSeq",
    ]

    def extract_imageSeq(self, packager):
        """Extract per renderlayer that has AOVs (Arbitrary Output Variable)
        """
        packager.skip_stage()
        package_path = packager.create_package()

        self.log.info("Extracting render output..")
        self.add_sequence(packager, self.data["outputPath"], package_path)

    def add_sequence(self, packager, seq_path, package_path):
        """
        """
        seq_dir, pattern = os.path.split(seq_path)

        self.log.info("Collecting sequence from: %s" % seq_dir)
        assert os.path.isdir(seq_dir), "Sequence dir not exists."

        # (NOTE) Did not consider frame step (byFrame)
        start_frame = self.data["startFrame"]
        end_frame = self.data["endFrame"]

        collections, _ = clique.assemble(os.listdir(seq_dir),
                                         patterns=[clique.PATTERNS["frames"]])

        assert len(collections), "Extraction failed, no sequence found."

        for sequence in collections:
            if pattern == (sequence.head +
                           "#" * sequence.padding +
                           sequence.tail):
                break
        else:
            raise Exception("No sequence match this pattern: %s" % pattern)

        entry_fname = (sequence.head +
                       "%%0%dd" % sequence.padding +
                       sequence.tail)

        project = self.context.data["projectDoc"]
        e_in, e_out, handles, _ = reveries.utils.get_timeline_data(project)

        packager.add_data({"sequence": {
            None: {
                "imageFormat": self.data["fileExt"],
                "fname": entry_fname,
                "seqSrcDir": seq_dir,
                "seqStart": list(sequence.indexes)[0],
                "seqEnd": list(sequence.indexes)[-1],
                "startFrame": start_frame,
                "endFrame": end_frame,
                "byFrameStep": self.data["byFrameStep"],
                "edit_in": e_in,
                "edit_out": e_out,
                "handles": handles,
                "resolution": self.context.data["resolution"],
                "fps": self.context.data["fps"],
            }
        }})

        for file in [entry_fname % i for i in sequence.indexes]:
            src = seq_dir + "/" + file
            dst = os.path.join(package_path, file)
            packager.add_hardlink(src, dst)
