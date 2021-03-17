import os
import json

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

        self.files_info = {
            'geom': 'geom.usd',
            'hierarchy': 'hierarchy.json'
        }
        self.staging_dir = utils.stage_dir(dir=instance.data["_sharedStage"])
        self.shape_merge = instance.data.get("USD_shape_merge", False)

        # Update information in instance data
        instance.data["repr.USD._stage"] = self.staging_dir
        instance.data["repr.USD._files"] = [
            self.files_info['geom'], self.files_info['hierarchy']]
        instance.data["repr.USD.entryFileName"] = self.files_info['geom']
        instance.data["repr.USD.hierarchyFileName"] = self.files_info['hierarchy']

        instance.data["shape_merge"] = self.shape_merge

        self.export_usd()

    def export_usd(self):
        from reveries.maya.usd import load_maya_plugin

        load_maya_plugin()

        # === Export geom.usd === #
        self._export_geom()

        # === Export hierarchy === #
        self._export_hierarchy()

        self.log.info('Export model usd done.')

    def _export_geom(self):
        import maya.cmds as cmds
        from reveries.maya.usd.maya_export import MayaUsdExporter

        outpath = os.path.join(self.staging_dir, self.files_info['geom'])

        cmds.select('ROOT')
        exporter = MayaUsdExporter(export_path=outpath)
        exporter.exportUVs = True
        exporter.mergeTransformAndShape = True  # self.shape_merge
        exporter.animation = False
        exporter.export()

        self.log.info('Export geom usd done.')

    def _export_hierarchy(self):
        from reveries.maya import utils

        skip_type = [
            'parentConstraint',
            'scaleConstraint'
        ]

        hierarchy_obj = utils.HierarchyGetter(skip_type=skip_type)
        hierarchy_tree = hierarchy_obj.get_hierarchy('ROOT')

        json_path = os.path.join(self.staging_dir, self.files_info['hierarchy'])
        with open(json_path, 'w') as f:
            json.dump(hierarchy_tree, f, ensure_ascii=False, indent=4)
