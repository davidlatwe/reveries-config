
import os
import pyblish.api
import reveries.utils
from reveries import plugins
from reveries.maya import utils


class ExtractRender(plugins.PackageExtractor):
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

        self.log.info("Computing render output path..")

        # Computing output path may take a while
        output_dir = instance.context.data["outputDir"]
        output_paths = utils.get_output_paths(output_dir,
                                              instance.data["renderer"],
                                              instance.data["renderlayer"],
                                              instance.data["camera"])
        instance.data["outputPaths"] = output_paths

        # Assume the rendering has been completed at this time being,
        # start to check and extract the rendering outputs
        for aov_name, aov_path in output_paths.items():
            self.compute_filenames(instance, aov_path, aov_name, package_path)

        self.render()

    def compute_filenames(self, instance, aov_path, aov_name, package_path):
        """
        """
        from maya import cmds

        seq_dir, pattern = os.path.split(aov_path)

        # (NOTE) Did not consider frame step (byFrame)
        start_frame = instance.data["startFrame"]
        end_frame = instance.data["endFrame"]
        by_frame = instance.data["byFrameStep"]

        project = instance.context.data["projectDoc"]
        e_in, e_out, handles, _ = reveries.utils.get_timeline_data(project)
        camera = instance.data["camera"]

        packager = instance.data["packager"]
        packager.add_data({"sequence": {
            aov_name: {
                "imageFormat": instance.data["fileExt"],
                "fname": pattern,
                "seqSrcDir": seq_dir,
                "startFrame": start_frame,
                "endFrame": end_frame,
                "byFrameStep": by_frame,
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

    @plugins.delay_extract
    def render(self):
        pass
