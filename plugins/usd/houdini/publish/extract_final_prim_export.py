import os
import pyblish.api


class ExtractFinalShotUSDExport(pyblish.api.InstancePlugin):
    order = pyblish.api.ExtractorOrder + 0.23
    hosts = ["houdini"]
    label = "Extract Final USD Export"
    families = [
        "reveries.final.usd",
    ]

    def process(self, instance):
        from reveries import utils

        asset_doc = instance.data["assetDoc"]
        self.shot_name = asset_doc["name"]

        staging_dir = utils.stage_dir()

        # Update information in instance data
        file_name = 'final_prim.usda'
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [file_name]
        instance.data["repr.USD.entryFileName"] = file_name

        # === Export USD file === #
        output_path = os.path.join(staging_dir, file_name)
        self._export_usd(output_path)

        self._publish_instance(instance)

    def _export_usd(self, output_path):
        from reveries.common.usd.pipeline import final_prim_export

        builder = final_prim_export.FinalUsdBuilder(
            shot_name=self.shot_name
        )
        builder.export(output_path)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance
        publish_instance.run(instance)

        instance.data["_preflighted"] = True
