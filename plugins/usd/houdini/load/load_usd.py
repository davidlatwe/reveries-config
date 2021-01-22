import os

import avalon.api
from reveries.houdini.plugins import HoudiniUSDBaseLoader


def env_embedded_path(path):
    """Embed environment var `$AVALON_PROJECTS` and `$AVALON_PROJECT` into path

    This will ensure reference or cache path resolvable when project root
    moves to other place.

    """
    path = path.replace(
        avalon.api.registered_root(), "$AVALON_PROJECTS", 1
    )
    path = path.replace(
        avalon.Session["AVALON_PROJECT"], "$AVALON_PROJECT", 1
    )

    return path


class USDLoader(HoudiniUSDBaseLoader, avalon.api.Loader):
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
        "reveries.ani.ani_prim",
        "reveries.setdress.layer_prim",
        "reveries.setdress.usd",
        "reveries.layout.usd",
        "reveries.camera.usd",
        "reveries.camera",
        "reveries.final.usd",
        "reveries.fx.usd",
        "reveries.fx.layer_prim",
        "reveries.lgt.usd",
        "reveries.ani.usd",
        "reveries.rig.usd",
        "reveries.skeletoncache"
    ]

    representations = [
        "USD",
    ]

    def load(self, context, name=None, namespace=None, data=None):
        import hou
        from avalon.houdini import pipeline
        from reveries.common.utils import project_root_path

        # Get usd file
        representation = context["representation"]
        entry_path = self.file_path(representation)
        usd_file = os.path.expandvars(entry_path).replace("\\", "/")

        if not usd_file:
            # Check publish folder exists
            directory = self.package_path
            if not os.path.exists(str(directory)):
                hou.ui.displayMessage(
                    "Publish folder not exists:\n{}".format(directory),
                    severity=hou.severityType.Warning
                )
                return

            # Check usd file already published
            files = os.listdir(directory)
            if not files:
                hou.ui.displayMessage(
                    "Can't found usd file in publish folder:\n{}".format(directory),
                    severity=hou.severityType.Warning)
                return
            usd_file = os.path.join(directory, files[0]).replace("\\", "/")

        # Update os environ
        usd_file = project_root_path(usd_file)

        asset_name = context['asset']['name']
        subset_data = context['subset']

        usd_info = {
            'asset_name': asset_name,
            'subset_name': subset_data['name'],
            'family_name': subset_data['data']['families'],
            'file_path': usd_file
        }

        index, node = self._add_usd(usd_info)

        # Create container
        obj = hou.node("/obj")
        node_name = "{}_{}".format(node.name(), index)
        obj.createNode("geo", node_name=node_name)
        extra_data = {
            "subnet_usd_path": node.path(),
            "usd_index": str(index)
        }

        container = pipeline.containerise(
            node_name, asset_name, [], context,
            self.__class__.__name__,
            extra_data=extra_data
        )

        node.setSelected(1, 1)
        return container

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
        from reveries.houdini.usd.add_usd_file import update_node

        stage = hou.node("/stage/")

        # Check selective node
        node = hou.selectedNodes()
        if not node:
            node = stage.createNode("subnet_usd_2", 'subnet_usd')
            node.moveToGoodPosition()
        else:
            node_type = node[0].type().name()
            if node_type == "subnet_usd_2":
                node = node[0]
            else:
                node = stage.createNode("subnet_usd_2", 'subnet_usd')
                node.moveToGoodPosition()

        index = update_node(node, usd_info)
        self.log.info('Current node: {}'.format(node))
        self.log.info('Add done.\nInfo: {}\n'.format(usd_info))

        return index, node
