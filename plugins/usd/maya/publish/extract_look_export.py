import os
import contextlib
import pyblish.api


class ExtractLookUSDExport(pyblish.api.InstancePlugin):
    """Publish look/assign usd file

    This plug-in takes will publish look.usd and assign.usd

    """

    order = pyblish.api.ExtractorOrder + 0.21
    hosts = ["maya"]
    label = "Extract LookDev USD Export"
    families = [
        "reveries.look",
    ]

    def process(self, instance):

        from reveries import utils

        asset_doc = instance.data["assetDoc"]
        self.asset_name = asset_doc["name"]

        self.files_info = {
            'assign': 'assign.usda',
            'look': 'look.usda',
            # 'prim': 'mod_{}.usda'.format(self.asset_name)
        }

        self.staging_dir = utils.stage_dir()
        # subset_name = instance.data["subset"]

        # Update information in instance data
        instance.data["repr.USD._stage"] = self.staging_dir
        instance.data["repr.USD._files"] = [
            self.files_info['assign'],
            self.files_info['look']
        ]

        self.export_usd()
        self._publish_instance(instance)

    def export_usd(self):
        from reveries.usd.utils import load_maya_plugin

        load_maya_plugin()

        # === Export assign.usd === #
        outpath = os.path.join(self.staging_dir, self.files_info['assign'])
        self._export_assign(outpath)

        # === Export look.usd === #
        outpath = os.path.join(self.staging_dir, self.files_info['look'])
        self._export_looks(outpath)

        print 'Export assign/look usd done.'

    def _export_assign(self, outpath):
        import maya.cmds as cmds

        from reveries.usd.utils import assign_export

        cmds.select('ROOT')
        sel = cmds.ls(sl=True)[0]
        assign_export.export(sel, merge=True, outPath=outpath)

    def _export_looks(self, outpath):
        import maya.cmds as cmds

        from reveries.usd.utils import looks_export

        cmds.select('ROOT')
        looks_export.export(file_path=outpath)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.new_utils import publish_instance
        publish_instance.run(instance)

        instance.data["published"] = True

        # context = instance.context
        # context.remove(instance)
