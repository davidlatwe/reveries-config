
import os
import pyblish.api


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
        from reveries.maya import utils as maya_utils

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

        if renderer == "arnold":
            self.get_arnold_extra_aov_outputs(staging_dir,
                                              renderlayer,
                                              camera,
                                              outputs)

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

            start = int(instance.data["startFrame"])
            end = int(instance.data["endFrame"])
            step = int(instance.data["step"])

            fname = pattern.replace(padding_str, frame_str)
            for frame_num in range(start, end + 1, step):
                files.append(fname % frame_num)

        instance.data["outputPaths"] = outputs

        instance.data["repr.renderLayer._stage"] = staging_dir
        instance.data["repr.renderLayer._hardlinks"] = files
        instance.data["repr.renderLayer.sequence"] = sequence
        instance.data["repr.renderLayer._delayRun"] = {
            "func": self.render,
        }

    def get_arnold_extra_aov_outputs(self,
                                     staging_dir,
                                     layer,
                                     camera,
                                     outputs):
        from maya import cmds
        from mtoa import aovs
        from reveries.maya import arnold, capsule, utils as maya_utils

        all_groups = arnold.get_all_light_groups()
        lighting_aovs = aovs.getLightingAOVs()
        fnprefix = maya_utils.get_render_filename_prefix(layer)

        def setext(path, ext):
            path, _ = os.path.splitext(path)
            return path + "." + ext

        for aov_node in arnold.get_arnold_aov_nodes(layer):
            aov_name = cmds.getAttr(aov_node + ".name")

            drivers = cmds.listConnections(aov_node + ".outputs[*].driver",
                                           source=True,
                                           destination=False) or []
            all_exr = all(cmds.getAttr(d + ".aiTranslator") == "exr"
                          for d in drivers)

            # Get light groups

            if aov_name in lighting_aovs:
                if cmds.getAttr(aov_node + ".lightGroups"):
                    # All light groups
                    if all_exr:
                        # ALl light groups get merged in *batch* and
                        # all drivers are set to EXR
                        groups = ["lgroups"]
                    else:
                        groups = all_groups[:]
                else:
                    group_list = cmds.getAttr(aov_node + ".lightGroupsList")
                    groups = [grp for grp in group_list.split(" ") if grp]
            else:
                groups = []

            # Compute outputs from all drivers

            if aov_name == "RGBA":
                aov_name = "beauty"

            for i, driver in enumerate(drivers):
                if i == 0:
                    driver_suffix = ""
                else:
                    driver_suffix = "_%d" % i

                ext = cmds.getAttr(driver + ".aiTranslator")

                if driver_suffix:
                    prefix = fnprefix + driver_suffix
                    with capsule.attribute_values({
                        "defaultRenderGlobals.imageFilePrefix": prefix
                    }):
                        pattern = maya_utils.compose_render_filename(layer,
                                                                     aov_name,
                                                                     camera)
                        aov_dv_name = aov_name + driver_suffix
                        output_path = staging_dir + "/" + setext(pattern, ext)
                        outputs[aov_dv_name] = output_path.replace("\\", "/")

                for group in groups:
                    prefix = fnprefix + "_" + group + driver_suffix
                    with capsule.attribute_values({
                        "defaultRenderGlobals.imageFilePrefix": prefix
                    }):
                        pattern = maya_utils.compose_render_filename(layer,
                                                                     aov_name,
                                                                     camera)
                        aov_lg_name = aov_name + "_" + group + driver_suffix
                        output_path = staging_dir + "/" + setext(pattern, ext)
                        outputs[aov_lg_name] = output_path.replace("\\", "/")

    def render(self):
        pass
