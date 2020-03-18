
import os
import json
import pyblish.api
import reveries.utils
import reveries.lib

from avalon.vendor import clique
# from reveries.plugins import DelegatablePackageExtractor
from reveries.plugins import PackageExtractor
from reveries.maya import utils


class ExtractRender(PackageExtractor):
    """Start GUI rendering if not delegate to Deadline
    """

    label = "Extract Render"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]

    families = [
        "reveries.renderlayer",
    ]

    representations = [
        "renderLayer",
    ]

    def extract_renderLayer(self, instance):
        """Extract per renderlayer that has AOVs (Arbitrary Output Variable)
        """
        packager = instance.data["packager"]
        packager.skip_stage()
        package_path = packager.create_package()
        data_path = os.path.join(package_path, ".remoteData.json")

        if reveries.lib.in_remote():
            # Render job completed, running publish job in Deadline
            self.log.info("Reading render output path from disk..")

            with open(data_path, "r") as fp:
                output_paths = json.load(fp)

            self.log.info("Extracting render output..")
            # Assume the rendering has been completed at this time being,
            # start to check and extract the rendering outputs
            for aov_name, aov_path in output_paths.items():
                self.add_sequence(instance, aov_path, aov_name, package_path)

        else:
            # About to submit render job
            self.log.info("Computing render output path and save to disk..")

            # Computing output path may take a while
            output_dir = instance.context.data["outputDir"]
            output_paths = utils.get_output_paths(output_dir,
                                                  instance.data["renderer"],
                                                  instance.data["renderlayer"],
                                                  instance.data["camera"])
            instance.data["outputPaths"] = output_paths
            # Save to disk for later use
            with open(data_path, "w") as fp:
                json.dump(output_paths, fp, indent=4)

            self.log.info("Ready to submit render job..")

    def add_sequence(self, instance, aov_path, aov_name, package_path):
        """
        """
        from maya import cmds

        seq_dir, pattern = os.path.split(aov_path)

        self.log.info("Collecting sequence from: %s" % seq_dir)
        assert os.path.isdir(seq_dir), "Sequence dir not exists."

        # (NOTE) Did not consider frame step (byFrame)
        start_frame = instance.data["startFrame"]
        end_frame = instance.data["endFrame"]

        patterns = [
            clique.PATTERNS["frames"],
            clique.DIGITS_PATTERN,
        ]
        minimum_items = 1 if start_frame == end_frame else 2
        collections, _ = clique.assemble(os.listdir(seq_dir),
                                         patterns=patterns,
                                         minimum_items=minimum_items)

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

        project = instance.context.data["projectDoc"]
        e_in, e_out, handles, _ = reveries.utils.get_timeline_data(project)
        camera = instance.data["camera"]

        packager = instance.data["packager"]
        packager.add_data({"sequence": {
            aov_name: {
                "imageFormat": instance.data["fileExt"],
                "fname": entry_fname,
                "seqSrcDir": seq_dir,
                "seqStart": list(sequence.indexes)[0],
                "seqEnd": list(sequence.indexes)[-1],
                "startFrame": start_frame,
                "endFrame": end_frame,
                "byFrameStep": instance.data["byFrameStep"],
                "edit_in": e_in,
                "edit_out": e_out,
                "handles": handles,
                "focalLength": cmds.getAttr(camera + ".focalLength"),
                "resolution": instance.data["resolution"],
                "fps": instance.context.data["fps"],
                "cameraUUID": utils.get_id(camera),
                "renderlayer": instance.data["renderlayer"],
            }
        }})

        for file in [entry_fname % i for i in sequence.indexes]:
            src = seq_dir + "/" + file
            dst = os.path.join(package_path, aov_name, file)
            packager.add_hardlink(src, dst)
