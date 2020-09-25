import os
import subprocess

import avalon.api
from reveries.plugins import PackageLoader


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

    def _file_path(self, representation):
        file_name = representation["data"]["entryFileName"]
        entry_path = os.path.join(self.package_path, file_name)

        if not os.path.isfile(entry_path):
            raise IOError("File Not Found: {!r}".format(entry_path))

        return env_embedded_path(entry_path)

    def load(self, context, name, namespace, data):
        # Get usd file
        representation = context["representation"]
        entry_path = self._file_path(representation)
        usd_file = os.path.expandvars(entry_path).replace("\\", "/")

        if not usd_file:
            directory = self.package_path
            files = os.listdir(directory)
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