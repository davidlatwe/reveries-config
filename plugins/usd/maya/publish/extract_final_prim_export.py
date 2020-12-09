import os
import pyblish.api


class ExtractFinalShotUSDExport(pyblish.api.InstancePlugin):
    order = pyblish.api.ExtractorOrder + 0.4815
    hosts = ["maya"]
    label = "Extract Final USD Export"
    families = [
        "reveries.final.usd",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.common import get_frame_range
        from reveries.common.build_delay_run import DelayRunBuilder

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])

        # Update information in instance data
        file_name = 'final_prim.usda'
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [file_name]
        instance.data["repr.USD.entryFileName"] = file_name

        instance.data["_preflighted"] = True

        # Check frame range
        start_frame = instance.data.get("startFrame", None)
        end_frame = instance.data.get("endFrame", None)
        if not start_frame or not end_frame:
            shot_name = instance.data['asset']
            start_frame, end_frame = get_frame_range.get(shot_name)
            instance.data["startFrame"] = start_frame
            instance.data["endFrame"] = end_frame

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
            "reveries.ani.usd",
            "reveries.camera.usd",
        ]

        for _instance in context:
            if _instance.data["family"] in dependencies_family:
                dependencies.append(_instance)

        return dependencies

    def _export_usd(self, instance_data, context_data, output_path):
        from reveries.common.usd.pipeline import final_prim_export

        builder = final_prim_export.FinalUsdBuilder(
            shot_name=instance_data["asset"],
            frame_range=[
                instance_data.get("startFrame"), instance_data.get("endFrame")
            ]
        )
        builder.export(output_path)

        self._publish_instance(instance_data, context_data)

    def _publish_instance(self, instance_data, context_data):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance_data, context=context_data)
