import os
import json
import pyblish.api


class ExtractRigSkeletonExport(pyblish.api.InstancePlugin):
    """Export rig skeleton data usd file.
    """

    order = pyblish.api.ExtractorOrder + 0.2
    hosts = ["maya"]
    label = "Extract Rig Skeleton USD Export"
    families = [
        "reveries.rig.skeleton"
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.maya.usd import load_maya_plugin, asset_prim_export
        from reveries.maya.usd import skeldata_export

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])

        model_subset_data = instance.data["model_subset_data"]
        json_file_name = "model_subset_data.json"

        files_name = [
            skeldata_export.SKELDATA_SOURCE_NAME,  # r'skel_source.usda'
            skeldata_export.SKELDATA_NAME,  # r'skel_data.usda'
            json_file_name
        ]

        # Update information in instance data
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = files_name
        instance.data["repr.USD.entryFileName"] = skeldata_export.SKELDATA_NAME
        instance.data["repr.USD.modelDataFileName"] = "model_subset_data.json"

        load_maya_plugin()

        # Export rig skeleton usd
        skeldata_export.export(staging_dir, shape_merge=True)

        # Export model data
        json_path = os.path.join(staging_dir, json_file_name)
        with open(json_path, 'w') as f:
            json.dump(model_subset_data, f, ensure_ascii=False, indent=4)

        self.log.info('Export rig skeleton usd done.')

        self._publish_instance(instance)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance)

        instance.data["_preflighted"] = True
