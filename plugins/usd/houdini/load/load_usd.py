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
        # print('directory:', self.package_path)
        files = os.listdir(directory)
        # print('files:', files)
        if not files:
            print('No usd file found in : {}'.format(directory))
            return

        usd_file = os.path.join(directory, files[0])
        # self._open_usdview(usd_file)