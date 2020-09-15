import os
import pyblish.api


class ExtractModUSDExport(pyblish.api.InstancePlugin):
    """Publish model usd

    This plug-in will publish geom.usd file.
    We need to running this plugin before 'Extract Model(mb)/(abc)'.
    Because plug-in will add 'MOD' group under 'ROOT'.
    """

    order = pyblish.api.ExtractorOrder + 0.2
    hosts = ["maya"]
    label = "Extract Model USD Export"
    families = [
        "reveries.model"
    ]

    def process(self, instance):
        from reveries import utils

        asset_doc = instance.data["assetDoc"]
        self.asset_name = asset_doc["name"]

        self.files_info = {
            'geom': 'geom.usda',
        }

        self.staging_dir = utils.stage_dir()

        # Update information in instance data
        instance.data["repr.USD._stage"] = self.staging_dir
        instance.data["repr.USD._files"] = [self.files_info['geom']]
        instance.data["repr.USD.entryFileName"] = self.files_info['geom']

        self.export_usd()
        self._publish_instance(instance)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance
        publish_instance.run(instance)

        instance.data["published"] = True

        # context = instance.context
        # context.remove(instance)

    def export_usd(self):
        from reveries.maya.usd import load_maya_plugin

        load_maya_plugin()

        # === Export geom.usd === #
        outpath = os.path.join(self.staging_dir, self.files_info['geom'])
        self._export_geom(outpath)

        print 'Export geom usd done.'

    def _export_geom(self, outpath):
        import maya.cmds as cmds
        from reveries.maya.usd.maya_export import MayaUsdExporter

        cmds.select('ROOT')

        exporter = MayaUsdExporter(export_path=outpath, export_selected=True)
        exporter.exportUVs = True
        exporter.mergeTransformAndShape = True
        exporter.animation = False
        exporter.exportColorSets = True
        exporter.exportDisplayColor = True
        exporter.export()
