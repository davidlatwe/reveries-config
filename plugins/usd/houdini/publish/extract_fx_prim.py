import os

import pyblish.api


class ExtractFxPrimUSD(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.21
    label = "Extract Fx USD Export"
    # hosts = ["houdini"]
    families = [
        "reveries.fx.usd",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.common.build_delay_run import DelayRunBuilder

        # Set comment
        context = instance.context
        context.data["comment"] = "Auto generate"

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        filename = 'fx_prim.usda'

        output_path = os.path.join(staging_dir, filename)

        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [filename]
        instance.data["repr.USD.entryFileName"] = filename

        instance.data["_preflighted"] = True
        instance.data["deadline_script_only"] = True

        # Create delay running
        delay_builder = DelayRunBuilder(instance)

        instance.data["deadline_plugin"] = "HoudiniBatch"

        instance.data["repr.USD._delayRun"] = {
            "func": self.export_usd,
            "args": [
                delay_builder.instance_data, delay_builder.context_data,
                output_path
            ],
        }

        instance.data["deadline_dependency"] = self.get_deadline_dependency(
            instance)

    def get_deadline_dependency(self, instance):
        context = instance.context
        dependencies = []

        dependencies_family = ["reveries.fx.layer_prim"]

        for _instance in context:
            if _instance.data["family"] in dependencies_family:
                dependencies.append(_instance)

        return dependencies

    def export_usd(self, instance_data, context_data, output_path):
        from reveries.common.usd.pipeline import fx_prim_export

        # Export fxPrim
        shot_name = instance_data['asset']
        fx_prim_export.FxPrimExport.export(output_path, shot_name)

        # ==== Publish instance ==== #
        self._publish_instance(instance_data, context_data)

    def _publish_instance(self, instance_data, context_data=None):

        # === Publish instance === #
        from reveries.common.publish import publish_instance
        publish_instance.run(instance_data, context=context_data)
