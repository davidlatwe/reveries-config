
import os
import pyblish.api
from reveries.maya import utils as maya_utils


class ExtractRender(pyblish.api.InstancePlugin):
    """Start GUI rendering if not delegate to Deadline
    """

    label = "Extract Render"
    order = pyblish.api.ExtractorOrder
    hosts = ["maya"]

    families = [
        "reveries.renderlayer",
    ]

    def process(self, instance):
        """Extract per renderlayer that has AOVs (Arbitrary Output Variable)
        """
        from maya import cmds

        self.log.info("Computing render output path..")

        renderer = instance.data["renderer"]
        renderlayer = instance.data["renderlayer"]
        camera = instance.data["camera"]

        # Computing output path may take a while
        staging_dir = instance.context.data["outputDir"]
        outputs = maya_utils.get_output_paths(staging_dir,
                                              renderer,
                                              renderlayer,
                                              camera)
        padding = maya_utils.get_render_padding(renderer)
        padding_str = "#" * padding
        frame_str = "%%0%dd" % padding

        # Assume the rendering has been completed at this time being,
        # start to check and extract the rendering outputs
        sequence = dict()
        files = list()
        for aov_name, aov_path in outputs.items():

            pattern = os.path.relpath(aov_path, staging_dir)

            sequence[aov_name] = {
                "imageFormat": instance.data["fileExt"],
                "fpattern": pattern,
                "focalLength": cmds.getAttr(camera + ".focalLength"),
                "resolution": instance.data["resolution"],
                "cameraUUID": maya_utils.get_id(camera),
                "renderlayer": renderlayer,
            }

            start = instance.data["startFrame"]
            end = instance.data["endFrame"]
            step = instance.data["step"]

            fname = pattern.replace(padding_str, frame_str)
            for frame_num in range(start, end, step):
                files.apppend(fname % frame_num)

        instance.data["outputPaths"] = outputs

        instance.data["repr.renderLayer._stage"] = staging_dir
        instance.data["repr.renderLayer._hardlinks"] = files
        instance.data["repr.renderLayer.sequence"] = sequence
        instance.data["repr.renderLayer._delayRun"] = {
            "func": self.render,
        }

    def render(self):
        pass
