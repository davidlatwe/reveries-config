import os
import imp

import pyblish.api
import avalon


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

        # Check renderer from db
        self.renderer = instance.data.get('renderer', None)
        assert self.renderer, "There is no renderer setting in db. Please check with TD."

        asset_doc = instance.data["assetDoc"]
        self.asset_name = asset_doc["name"]

        self.files_info = {
            'assign': 'assign.usda',
            'look': 'look.usda',
        }

        self.staging_dir = utils.stage_dir()

        # Update information in instance data
        instance.data["repr.USD._stage"] = self.staging_dir
        instance.data["repr.USD._files"] = [
            self.files_info['assign'],
            self.files_info['look']
        ]

        self.export_usd()
        self._publish_instance(instance)

    def export_usd(self):
        import pymel.core as pm
        from reveries.maya.usd import load_maya_plugin

        load_maya_plugin()

        # === Check model is reference or not === #
        root_node = 'ROOT'
        all_ref = pm.listReferences()
        if all_ref:
            for ref in all_ref:
                _path = ref.unresolvedPath()
                if '/publish/modelDefault/' in _path:
                    ns = ref.namespace
                    root_node = '{}:ROOT'.format(ns)

        # === Export assign.usd === #
        outpath = os.path.join(self.staging_dir, self.files_info['assign'])
        self._export_assign(outpath, root_node)

        # === Export look.usd === #
        outpath = os.path.join(self.staging_dir, self.files_info['look'])
        self._export_looks(outpath, root_node)

        print 'Export assign/look usd done.'

    def _export_assign(self, outpath, root_node):
        """
        Export assign.usd file
        :param outpath: (str) Output file path
        :param root_node: (str) The name of "ROOT" node. Default is "ROOT". When the model is reference, the root name
            is "<namespace>:ROOT", eg BoxB_model_01_:ROOT
        :return:
        """
        import maya.cmds as cmds
        from reveries.maya.usd import assign_export

        cmds.select(root_node)
        sel = cmds.ls(sl=True)[0]
        assign_export.export(sel, merge=True, outPath=outpath)

    def _export_looks(self, outpath, root_node):
        import maya.cmds as cmds

        # Get look exporter python file
        py_file = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "..\\..\\..\\..\\reveries\\maya\\usd\\{}\\looks_export.py").format(self.renderer))

        if not os.path.exists(py_file):
            assert False, "Cannot found look exporter py file: {}".format(py_file)
        looks_export = imp.load_source('looks_export', py_file)

        cmds.select(root_node)
        looks_export.export(file_path=outpath)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.new_utils import publish_instance
        publish_instance.run(instance)

        instance.data["published"] = True

        # context = instance.context
        # context.remove(instance)
