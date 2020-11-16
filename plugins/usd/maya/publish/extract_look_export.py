import os
import contextlib
import importlib

import pyblish.api


class ExtractLookUSDExport(pyblish.api.InstancePlugin):
    """Publish look/assign usd file

    This plug-in will publish look.usd and assign.usd

    """

    order = pyblish.api.ExtractorOrder + 0.21
    hosts = ["maya"]
    label = "Extract LookDev USD Export"
    families = [
        "reveries.look",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.common import skip_instance

        context = instance.context
        if skip_instance(context, ['reveries.xgen']):
            return

        # Check renderer from db
        self.renderer = instance.data.get('renderer', None)
        assert self.renderer, \
            "There is no renderer setting in db. Please check with TD."

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

        self.export_usd(instance)

    def export_usd(self, instance):
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
        self._export_looks(instance, outpath, root_node)

        # === Switch texture path to published path === #
        # self._switch_tex_path(instance, outpath)

        self.log.info('Export assign/look usd done.')

    def _export_assign(self, outpath, root_node):
        """
        Export assign.usd file
        :param outpath: (str) Output file path
        :param root_node: (str) The name of "ROOT" node. Default is "ROOT".
            When the model is reference, the root name is "<namespace>:ROOT",
            e.g. BoxB_model_01_:ROOT
        :return:
        """
        import maya.cmds as cmds
        from reveries.maya.usd import assign_export

        cmds.select(root_node)
        sel = cmds.ls(sl=True)[0]
        assign_export.export(sel, merge=True, outPath=outpath)

    def _export_looks(self, instance, outpath, root_node):
        from avalon import maya
        import maya.cmds as cmds
        from reveries.maya import capsule

        # Get look exporter python file
        py_file = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "..\\..\\..\\..\\reveries\\maya\\usd\\{}\\looks_export.py"
        ).format(self.renderer))

        if not os.path.exists(py_file):
            assert False, \
                "Cannot found look exporter py file: {}".format(py_file)

        looks_export = importlib.import_module(
            "reveries.maya.usd.{}.looks_export".format(self.renderer)
        )
        file_node_attrs = self._get_file_node_attrs(instance)

        with contextlib.nested(
                maya.maintained_selection(),
                capsule.ref_edit_unlock(),
                # (NOTE) Ensure attribute unlock
                capsule.attribute_states(file_node_attrs.keys(), lock=False),
                # Change to published path
                capsule.attribute_values(file_node_attrs),
                capsule.no_refresh(),
        ):
            cmds.select(root_node)
            looks_export.export(file_path=outpath)

    def _get_file_node_attrs(self, instance):
        # Change texture path to published path
        child_instances = instance.data.get("childInstances", [])
        try:
            texture = next(chd for chd in child_instances
                           if chd.data["family"] == "reveries.texture")
        except StopIteration:
            file_node_attrs = dict()
        else:
            file_node_attrs = texture.data.get("fileNodeAttrs", dict())

        # Replace root
        root_path = "{}/{}/".format(
            os.environ["AVALON_PROJECTS"],
            os.environ["AVALON_PROJECT"]
        )  # "Q:/199909_AvalonPlay/"
        _tag = "$AVALON_PROJECTS/$AVALON_PROJECT/"

        for attr, value in file_node_attrs.items():
            if isinstance(value, (str, unicode)):
                if _tag in value:
                    file_node_attrs[attr] = value.replace(_tag, root_path)

        return file_node_attrs
