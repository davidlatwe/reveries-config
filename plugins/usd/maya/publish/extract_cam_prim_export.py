import os
import json

import pyblish.api


class ExtractCameraPrimUSDExport(pyblish.api.InstancePlugin):
    """
    Export cam_prim USD.
    """

    order = pyblish.api.ExtractorOrder + 0.4801
    hosts = ["maya"]
    label = "Extract Camera Prim USD Export"
    families = [
        "reveries.camera.usd"
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.common.build_delay_run import DelayRunBuilder

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])

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

        instance.data["_preflighted"] = True

        # Create delay running
        delay_builder = DelayRunBuilder(instance)

        instance.data["repr.USD._delayRun"] = {
            "func": self._export_usd,
            "args": [
                delay_builder.instance_data, delay_builder.context_data
            ],
            "kwargs": {
                "usd_output_path": usd_output_path,
                "json_output_path": json_output_path,
            }
        }
        instance.data["deadline_dependency"] = \
            self.get_deadline_dependency(instance)

    def get_deadline_dependency(self, instance):
        context = instance.context
        dependencies = []

        dependencies_family = ["reveries.camera"]

        for _instance in context:
            if _instance.data["family"] in dependencies_family:
                dependencies.append(_instance)

        return dependencies

    def _export_usd(self, instance_data, context_data,
                    usd_output_path=None, json_output_path=None):

        from reveries.common.usd.pipeline import cam_prim_export

        shot_name = instance_data["asset"]

        # Export cam_prim.usd
        self.log.info("Export camPrim for {}".format(shot_name))
        cam_prim_export.export(shot_name, usd_output_path)

        self._export_json(usd_output_path, json_output_path)

        self._publish_instance(instance_data, context_data)

        self.log.info('Export camera prim usd done.')

    def _export_json(self, usd_path=None, json_path=None):
        from reveries.common.usd.get_asset_info import GetAssetInfo

        asset_obj = GetAssetInfo(usd_file=usd_path)
        asset_info_data = asset_obj.asset_info

        with open(json_path, 'w') as f:
            json.dump(asset_info_data, f, ensure_ascii=False, indent=4)

    def _publish_instance(self, instance_data, context_data):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance_data, context=context_data)
