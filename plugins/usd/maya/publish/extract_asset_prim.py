import os
import contextlib
import pyblish.api
from avalon import io, api


class ExtractAssetPrimUSDExport(pyblish.api.InstancePlugin):
    """Produce a stripped down Maya file from instance

    This plug-in takes into account only nodes relevant to models
    and discards anything else, especially deformers along with
    their intermediate nodes.

    """

    order = pyblish.api.ExtractorOrder + 0.22
    hosts = ["maya"]
    label = "Extract Asset Prim USD Export"
    families = [
        "reveries.look.asset_prim"
    ]

    def process(self, instance):
        from pxr import Usd, UsdGeom

        from reveries import utils
        from reveries.usd.utils import load_maya_plugin
        from reveries.new_utils import get_publish_files

        asset_doc = instance.data["assetDoc"]
        asset_name = asset_doc["name"]

        staging_dir = utils.stage_dir()

        file_name = 'asset_prim.usda'

        # Update information in instance data
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [file_name]
        instance.data["repr.USD.entryFileName"] = file_name

        # Get asset id
        _filter = {"type": "asset", "name": asset_name}
        asset_id = io.find_one(_filter)['_id']

        load_maya_plugin()

        subsets = ['renderPrim', 'proxyPrim']
        usd_files = {}

        for subset_name in subsets:
            _filter = {
                "type": "subset",
                "name": subset_name,
                "parent": asset_id
            }
            # print('subset_name: ', subset_name)
            subset_data = io.find_one(_filter)
            if subset_data:
                subset_id = subset_data['_id']
                usd_files[subset_name] = get_publish_files.get_files(subset_id).get('USD', [])

        stage = Usd.Stage.CreateInMemory()

        UsdGeom.Xform.Define(stage, "/ROOT")
        rootPrim = stage.GetPrimAtPath('/ROOT')
        stage.SetDefaultPrim(rootPrim)

        root_layer = stage.GetRootLayer()

        for _, paths in usd_files.items():
            if paths:
                root_layer.subLayerPaths.append(paths[0])

        # print(stage.GetRootLayer().ExportToString())
        output_path = os.path.join(staging_dir, file_name)
        stage.GetRootLayer().Export(output_path)

        print 'Export asset prim usd done.'
