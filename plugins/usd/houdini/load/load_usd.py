import os
import subprocess

import avalon.api
from reveries.plugins import PackageLoader


class HoudiniUSDLoader(PackageLoader, avalon.api.Loader):
    """Load the model"""

    label = "Load USD"
    order = -10
    icon = "download"
    color = "orange"

    hosts = ["houdini"]

    families = [
        "reveries.model",
        "reveries.pointcache",
        "reveries.look.asset_prim",
        "reveries.ani.ani_prim"
    ]

    representations = [
        "USD",
    ]

    def load(self, context, name, namespace, data):
        directory = self.package_path
        files = os.listdir(directory)

        if not files:
            print('No usd file found in : {}'.format(directory))
            return

        usd_file = os.path.join(directory, files[0])
        asset_name = context['asset']['name']
        subset_data = context['subset']

        usd_info = {
            'asset_name': asset_name,
            'subset_name': subset_data['name'],
            'family_name': subset_data['data']['families'],
            'file_path': usd_file
        }

        self._add_usd(usd_info)

    def _add_usd(self, usd_info):
        """
        Add reference/sublayer in subnet node.
        :param usd_info: dict.
        usd_info = {
            'asset_name': 'BoxB',
            'subset_name': 'assetPrim',
            'family_name': 'reveries.look.asset_prim',
            'file_path': "Q:/199909_AvalonPlay/Avalon/PropBox/BoxB/publish/assetPrim/v002/USD/asset_prim.usda"
        }
        :return:
        """
        import hou
        from reveries.usd.houdini_utils.add_usd_file import update_node

        stage = hou.node("/stage/")
        # node = stage.createNode("subnet_usd","subnet_usd_tt")

        node = hou.selectedNodes()
        if not node:
            node = stage.createNode("subnet_usd", 'subnet_usd')
        else:
            node = node[0]

        # node = hou.node("/stage/subnet_usd_tt")

        update_node(node, usd_info)
        print 'Current node: {}'.format(node)
        print 'Add done.\nInfo: {}\n'.format(usd_info)
