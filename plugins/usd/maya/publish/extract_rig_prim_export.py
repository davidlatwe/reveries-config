import os
import pyblish.api


class ExtractRigPrimExport(pyblish.api.InstancePlugin):
    """Export rig primitive usd file
    """

    order = pyblish.api.ExtractorOrder + 0.201
    hosts = ["maya"]
    label = "Extract Rig Prim USD Export"
    families = [
        "reveries.rig.usd"
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.maya.usd import load_maya_plugin
        from reveries.maya.usd import rig_prim_export

        staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])

        file_name = 'rig_prim.usda'

        # Update information in instance data
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [file_name]
        instance.data["repr.USD.entryFileName"] = file_name

        load_maya_plugin()

        # Export rig prim usd
        output_path = os.path.join(staging_dir, file_name)

        exporter = rig_prim_export.RigPrimExporter(
            output_path,
            asset_name=instance.data['asset'],
            rig_subset_name=instance.data["subset"].replace("Prim", "")
        )
        exporter.export()

        self.log.info('Export rig prim usd done.')

        self._publish_instance(instance)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance)

        instance.data["_preflighted"] = True
