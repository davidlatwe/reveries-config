import os
import pyblish.api
from avalon import io, api


class ExtractAssetPrePrimUSDExport(pyblish.api.InstancePlugin):
    """Produce a stripped down Maya file from instance

    This plug-in takes into account only nodes relevant to models
    and discards anything else, especially deformers along with
    their intermediate nodes.

    """

    order = pyblish.api.IntegratorOrder + 0.131
    hosts = ["maya"]
    label = "Extract PrePrim USD Export"
    families = [
        "reveries.look.pre_prim"
    ]

    def look_ins_exists(self, context):
        look_instance_data = {}
        for instance in context:
            if instance.data["family"] == "reveries.look":
                look_instance_data["asset"] = instance.data["asset"]
                look_instance_data["subset"] = instance.data["subset"]
                look_instance_data["model_subset_id"] = instance.data.get("model_subset_id", "")
                break
        return look_instance_data

    def process(self, instance):
        from reveries import utils
        from reveries.maya.usd import load_maya_plugin
        from reveries.maya.usd.asset_pre_prim_export import prim_export

        asset_doc = instance.data["assetDoc"]
        asset_name = asset_doc["name"]
        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])

        # Check lookdev type. proxy or render.
        prim_type = instance.data["subset_type"]
        file_name = '{}_prim.usda'.format(prim_type)

        # Update information in instance data
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [file_name]

        load_maya_plugin()

        # Check look/model dependency
        self._check_look_dependency(instance)

        outpath = os.path.join(staging_dir, file_name)
        prim_export(asset_name, output_path=outpath, prim_type=prim_type)

        self.log.info('Export pre prim usd done.')

        self._publish_instance(instance)

    def _check_look_dependency(self, instance):
        context = instance.context

        look_instance_data = self.look_ins_exists(context)
        if look_instance_data.get("model_subset_id", ""):
            subset_id = look_instance_data["model_subset_id"]

            _filter = {'type': 'asset', 'name': look_instance_data["asset"]}
            shot_data = io.find_one(_filter)

            subset_filter = {
                'type': 'subset',
                'name': look_instance_data["subset"],
                'parent': shot_data['_id']
            }

            subset_data = [s for s in io.find(subset_filter)]

            if subset_data:
                subset_data = subset_data[0]

                if not subset_data["data"].get("model_subset_id", ""):
                    update = {
                        "data.model_subset_id": subset_id
                    }
                    io.update_many(subset_filter, update={"$set": update})

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance)

        instance.data["_preflighted"] = True
