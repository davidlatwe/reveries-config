
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
        import avalon.api

        self.log.info("Computing render output path..")

        context = instance.context
        staging_dir = context.data["outputDir"]

        repr_root = instance.data.get("reprRoot")
        if repr_root:
            # Re-direct output path to custom root path
            staging_dir = staging_dir.replace(avalon.api.registered_root(),
                                              repr_root,
                                              1)
            context.data["outputDir"] = staging_dir
            instance.data["repr.renderLayer.reprRoot"] = repr_root

        stereo_pairs = instance.data.get("stereo")
        if stereo_pairs is None:
            # Normal render
            camera = instance.data["camera"]
            outputs, sequence, files = self.compute_outputs(instance,
                                                            camera,
                                                            staging_dir)
            instance.data["outputPaths"] = outputs
            hardlinks = files

        else:
            # Stereo render
            left, right = stereo_pairs

            outputs_l, sequence, files_l = self.compute_outputs(instance,
                                                                left,
                                                                staging_dir,
                                                                stereo="Left")
            outputs_r, ________, files_r = self.compute_outputs(instance,
                                                                right,
                                                                staging_dir,
                                                                stereo="Right")
            instance.data["outputPaths"] = [outputs_l, outputs_r]
            instance.data["repr.renderLayer.stereo"] = True
            hardlinks = files_l + files_r

        # (NOTE) Save output dir for future hardlink cleanup
        instance.data["repr.renderLayer.outputDir"] = staging_dir
        instance.data["repr.renderLayer.sequence"] = sequence

        instance.data["repr.renderLayer._stage"] = staging_dir
        instance.data["repr.renderLayer._hardlinks"] = hardlinks
        instance.data["repr.renderLayer._delayRun"] = {
            "func": self.render,
        }

    def compute_outputs(self, instance, camera, staging_dir, stereo=None):
        from maya import cmds
        from reveries.maya import utils as maya_utils

        renderer = instance.data["renderer"]
        renderlayer = instance.data["renderlayer"]

        if stereo:
            stereo_rig = instance.data["camera"]
            camera_uuid = maya_utils.get_id(stereo_rig)
            focal = cmds.getAttr(stereo_rig + ".focalLength")
        else:
            camera_uuid = maya_utils.get_id(camera)
            focal = cmds.getAttr(camera + ".focalLength")

        # Computing output path may take a while
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
                "focalLength": focal,
                "resolution": instance.data["resolution"],
                "cameraUUID": camera_uuid,
                "renderlayer": renderlayer,
            }

            if stereo:
                stereo_formated = pattern.replace(stereo, "{stereo}")
                sequence[aov_name]["fpattern"] = stereo_formated

            start = int(instance.data["startFrame"])
            end = int(instance.data["endFrame"])
            step = int(instance.data["step"])

            fname = pattern.replace(padding_str, frame_str)
            for frame_num in range(start, end + 1, step):
                files.append(fname % frame_num)

        return outputs, sequence, files

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

        def setext(path, extension):
            path, _ = os.path.splitext(path)
            return path + "." + extension

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
