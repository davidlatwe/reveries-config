import os
import pyblish.api


class ExtractAssetPrimUSDExport(pyblish.api.InstancePlugin):
    """Publish asset_prim.usda
    """

    order = pyblish.api.IntegratorOrder + 0.132
    hosts = ["maya"]
    label = "Extract Asset Prim USD Export"
    families = [
        "reveries.look.asset_prim"
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.maya.usd import load_maya_plugin, asset_prim_export

        asset_doc = instance.data["assetDoc"]
        asset_name = asset_doc["name"]

        staging_dir = utils.stage_dir()

        file_name = 'asset_prim.usda'

        # Update information in instance data
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [file_name]
        instance.data["repr.USD.entryFileName"] = file_name

        load_maya_plugin()

        # Export asset prim usd
        output_path = os.path.join(staging_dir, file_name)
        asset_prim_export.export(asset_name, output_path)

        self.log.info('Export asset prim usd done.')

        self._publish_instance(instance)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance)

        instance.data["_preflighted"] = True
