import os
import json

import pyblish.api


class ExtractCameraPrimUSDExport(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.495
    hosts = ["maya"]
    label = "Extract Camera Prim USD Export"
    families = [
        "reveries.camera.usd"
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.common.usd.pipeline import cam_prim_export

        shot_name = instance.data['asset']
        staging_dir = utils.stage_dir()

        context_data = instance.context.data
        start = context_data["startFrame"]
        end = context_data["endFrame"]

        usd_name = 'cam_prim.usda'
        usd_output_path = os.path.join(staging_dir, usd_name)

        json_name = 'camera.json'
        json_output_path = os.path.join(staging_dir, json_name)


        # Update information in instance data
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [usd_name, json_name]
        instance.data["repr.USD.entryFileName"] = usd_name

        instance.data["startFrame"] = start
        instance.data["endFrame"] = end

        # Export cam_prim.usd
        cam_prim_export.export(shot_name, usd_output_path)

        self._export_json(usd_output_path, json_output_path)

        self._publish_instance(instance)

        self.log.info('Export camera prim usd done.')

    def _export_json(self, usd_path=None, json_path=None):
        from reveries.common.usd.get_asset_info import GetAssetInfo

        asset_obj = GetAssetInfo(usd_file=usd_path)
        asset_info_data = asset_obj.asset_info

        with open(json_path, 'w') as f:
            json.dump(asset_info_data, f, ensure_ascii=False, indent=4)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance)

        instance.data["_preflighted"] = True
