import os
import subprocess

import avalon.api
from reveries.plugins import PackageLoader


class OpenInUSD(PackageLoader, avalon.api.Loader):
    """Load the model"""

    label = "Open in USD view"
    order = -10
    icon = "list"
    color = "#56a6db"

    # hosts = ["maya"]

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
        self._open_usdview(usd_file)

    def _open_usdview(self, usd_file):
        # usd_file = r'F:\usd\test\data\OCEAN\Props\BallTwo\publish\modelDefault\v001\mod_BallTwo.usda'
        print('usd_file: {}'.format(usd_file))

        usdview_bat = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..\\..\\..\\usd\\template\\usdview.bat"))

        if not os.path.exists(usdview_bat):
            print('usdview.bat file not exists.')
            return

        cmd = [usdview_bat, usd_file]
        print('open usdview cmd: {}'.format(cmd))
        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
