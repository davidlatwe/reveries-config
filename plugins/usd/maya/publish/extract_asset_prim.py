import os
import pyblish.api


class ExtractAssetPrimUSDExport(pyblish.api.InstancePlugin):
    """Produce a stripped down Maya file from instance

    This plug-in takes into account only nodes relevant to models
    and discards anything else, especially deformers along with
    their intermediate nodes.

    """

    order = pyblish.api.ExtractorOrder + 0.23
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

        print 'Export asset prim usd done.'
