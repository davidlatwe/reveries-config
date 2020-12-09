import os
import pyblish.api


class ExtractAniShotUSDExport(pyblish.api.InstancePlugin):
    order = pyblish.api.ExtractorOrder + 0.4812
    hosts = ["maya"]
    label = "Extract Animation Shot USD"
    families = [
        "reveries.ani.usd",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.common import get_frame_range
        from reveries.common.build_delay_run import DelayRunBuilder

        start_frame = instance.data.get("startFrame")
        end_frame = instance.data.get("endFrame")

        if not start_frame or not end_frame:
            shot_name = instance.data['asset']
            start_frame, end_frame = get_frame_range.get(shot_name)
            instance.data["startFrame"] = start_frame
            instance.data["endFrame"] = end_frame

        # Update information in instance data
        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        file_name = 'ani_prim.usda'
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [file_name]
        instance.data["repr.USD.entryFileName"] = file_name
        instance.data["subsetGroup"] = "Animation"
        instance.data["_preflighted"] = True

        output_path = os.path.join(staging_dir, file_name)

        # Create delay running
        delay_builder = DelayRunBuilder(instance)

        instance.data["repr.USD._delayRun"] = {
            "func": self._export_usd,
            "args": [
                delay_builder.instance_data, delay_builder.context_data,
                output_path
            ],
        }
        instance.data["deadline_dependency"] = \
            self.get_deadline_dependency(instance)

    def get_deadline_dependency(self, instance):
        context = instance.context
        dependencies = []

        dependencies_family = [
            "reveries.pointcache",
            "reveries.camera.usd",
        ]

        for _instance in context:
            if _instance.data["family"] in dependencies_family:
                dependencies.append(_instance)

        return dependencies

    def _export_usd(self, instance_data, context_data, output_path):
        from reveries.maya.usd import ani_shot_export
        from reveries.maya.usd import load_maya_plugin

        self.log.info('\nStart export ani shot usd...')
        load_maya_plugin()

        builder = ani_shot_export.AniUsdBuilder(
            shot_name=instance_data["asset"],
            frame_in=instance_data.get("startFrame"),
            frame_out=instance_data.get("endFrame"),
        )
        builder.export(output_path)
        self._publish_instance(instance_data, context_data)
        self.log.info('Publish ani shot usd done.\n')

    def _publish_instance(self, instance_data, context_data):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance_data, context=context_data)
