import os
import contextlib
import pyblish.api
# import avalon.api
from avalon import io, api


class ExtractAniShotUSDExport(pyblish.api.InstancePlugin):
    """Produce a stripped down Maya file from instance

    This plug-in takes into account only nodes relevant to models
    and discards anything else, especially deformers along with
    their intermediate nodes.

    """

    order = pyblish.api.ExtractorOrder + 0.493
    hosts = ["maya"]
    label = "Extract Animation Shot USD"
    families = [
        "reveries.ani.ani_prim",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.usd.utils import load_maya_plugin

        asset_doc = instance.context.data["assetDoc"]
        self.shot_name = asset_doc["name"]

        self.frame_in = instance.data.get('startFrame', '')
        self.frame_out = instance.data('endFrame', '')

        staging_dir = utils.stage_dir()

        # Update information in instance data
        file_name = 'ani_prim.usda'
        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [file_name]
        instance.data["repr.USD.entryFileName"] = file_name

        # === Export USD file === #
        load_maya_plugin()

        output_path = os.path.join(staging_dir, file_name)
        self._export_usd(output_path)

        print 'Export ani shot usd done.'

    def _export_usd(self, output_path):
        from reveries.usd.utils import ani_shot_export
        # output_path = r'Q:\199909_AvalonPlay\Avalon\Shot\sh0100\work\animating\maya\scenes\usd\ani_shot.usda'

        builder = ani_shot_export.AniUsdBuilder(shot_name=self.shot_name,
                                                frame_in=self.frame_in,
                                                frame_out=self.frame_out)
        builder.export(output_path)
