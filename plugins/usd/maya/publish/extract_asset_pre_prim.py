import os
import pyblish.api


class ExtractAssetPrePrimUSDExport(pyblish.api.InstancePlugin):
    """Produce a stripped down Maya file from instance

    This plug-in takes into account only nodes relevant to models
    and discards anything else, especially deformers along with
    their intermediate nodes.

    """

    order = pyblish.api.ExtractorOrder + 0.22
    hosts = ["maya"]
    label = "Extract PrePrim USD Export"
    families = [
        "reveries.look.pre_prim"
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.maya.usd import load_maya_plugin
        from reveries.maya.usd.asset_pre_prim_export import prim_export

        asset_doc = instance.data["assetDoc"]
        asset_name = asset_doc["name"]
        staging_dir = utils.stage_dir()

        # Check lookdev type. proxy or render.
        prim_type = instance.data["subset_type"]
        file_name = '{}_prim.usda'.format(prim_type)

        # Update information in instance data
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [file_name]

        load_maya_plugin()

        outpath = os.path.join(staging_dir, file_name)
        prim_export(asset_name, output_path=outpath, prim_type=prim_type)

        print 'Export pre prim usd done.'

        self._publish_instance(instance)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.new_utils import publish_instance
        publish_instance.run(instance)

        instance.data["published"] = True

        # context = instance.context
        # context.remove(instance)

