import os

import avalon.api
from reveries.houdini.plugins import HoudiniBaseLoader


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


class HoudiniUSDLoader(HoudiniBaseLoader, avalon.api.Loader):
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
        "reveries.lgt.usd",
        "reveries.ani.usd"
    ]

    representations = [
        "USD",
    ]

    def _file_path(self, representation):
        file_name = representation["data"]["entryFileName"]
        entry_path = os.path.join(self.package_path, file_name)

        if not os.path.isfile(entry_path):
            raise IOError("File Not Found: {!r}".format(entry_path))

        return env_embedded_path(entry_path)

    def load(self, context, name=None, namespace=None, data=None):
        import hou

        root = context["project"]["data"]["root"]
        proj_name = context["project"]["name"]

        # Get usd file
        representation = context["representation"]
        entry_path = self._file_path(representation)
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
        project_root = r'{}/{}'.format(root, proj_name)
        if "PROJECT_ROOT" not in os.environ.keys():
            os.environ["PROJECT_ROOT"] = project_root
        usd_file = usd_file.replace(project_root, "$PROJECT_ROOT")

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

        update_node(node, usd_info)
        self.log.info('Current node: {}'.format(node))
        self.log.info('Add done.\nInfo: {}\n'.format(usd_info))
