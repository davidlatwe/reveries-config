import os
import pyblish.api


class ExtractModUSDExport(pyblish.api.InstancePlugin):
    """Publish model usd

    This plug-in will publish geom.usd file.
    """

    order = pyblish.api.ExtractorOrder + 0.2
    hosts = ["maya"]
    label = "Extract Model USD Export"
    families = [
        "reveries.model"
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.common import skip_instance

        if not instance.data.get("publishUSD", True):
            return

        context = instance.context
        if skip_instance(context, ['reveries.xgen']):
            return

        asset_doc = instance.data["assetDoc"]
        self.asset_name = asset_doc["name"]

        self.files_info = {
            'geom': 'geom.usd',
        }

        self.staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])

        # Update information in instance data
        instance.data["repr.USD._stage"] = self.staging_dir
        instance.data["repr.USD._files"] = [self.files_info['geom']]
        instance.data["repr.USD.entryFileName"] = self.files_info['geom']

        self.export_usd()

    def export_usd(self):
        from reveries.maya.usd import load_maya_plugin

        load_maya_plugin()

        # === Export geom.usd === #
        outpath = os.path.join(self.staging_dir, self.files_info['geom'])
        self._export_geom(outpath)

        self.log.info('Export geom usd done.')

    def _export_geom(self, outpath):
        import maya.cmds as cmds
        from reveries.maya.usd.maya_export import MayaUsdExporter

        # Rename uv set
        self._rename_uv_set("st")

        cmds.select('ROOT')
        exporter = MayaUsdExporter(export_path=outpath, export_selected=True)
        exporter.exportUVs = True
        exporter.mergeTransformAndShape = True
        exporter.animation = False
        exporter.exportColorSets = True
        exporter.exportDisplayColor = True
        exporter.export()

        self._rename_uv_set("map1")

    def _rename_uv_set(self, new_name):
        import maya.cmds as cmds

        meshs = cmds.listRelatives("ROOT", allDescendents=True, type="shape")
        for _mesh in meshs:
            uvset = cmds.polyUVSet(_mesh, query=True, currentUVSet=True)
            if uvset:
                if uvset[0] != new_name:
                    cmds.polyUVSet(
                        _mesh, rename=True, newUVSet=new_name, uvSet=uvset[0])
