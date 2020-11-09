import os
import pyblish.api


class ExtractAniShotUSDExport(pyblish.api.InstancePlugin):
    order = pyblish.api.ExtractorOrder + 0.493
    hosts = ["maya"]
    label = "Extract Animation Shot USD"
    families = [
        "reveries.ani.usd",
    ]

    def process(self, instance):
        import maya.cmds as cmds

        from reveries import utils
        from reveries.maya.usd import load_maya_plugin

        asset_doc = instance.data["assetDoc"]
        self.shot_name = asset_doc["name"]

        self.frame_in = instance.data.get(
            'startFrame',
            cmds.playbackOptions(query=True, ast=True)
        )
        self.frame_out = instance.data.get(
            'endFrame',
            cmds.playbackOptions(query=True, aet=True)
        )

        staging_dir = utils.stage_dir()

        # Update information in instance data
        file_name = 'ani_prim.usda'
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [file_name]
        instance.data["repr.USD.entryFileName"] = file_name
        instance.data["subsetGroup"] = "Animation"
        # instance.data["step_type"] = "ani_prim"

        # === Export USD file === #
        load_maya_plugin()

        output_path = os.path.join(staging_dir, file_name)
        self._export_usd(output_path)

        self._publish_instance(instance)

    def _export_usd(self, output_path):
        from reveries.maya.usd import ani_shot_export
        self.log.info('\nStart export ani shot usd...')

        builder = ani_shot_export.AniUsdBuilder(
            shot_name=self.shot_name,
            frame_in=self.frame_in,
            frame_out=self.frame_out
        )
        builder.export(output_path)
        self.log.info('Export ani shot usd done.\n')

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance
        publish_instance.run(instance)

        instance.data["_preflighted"] = True
