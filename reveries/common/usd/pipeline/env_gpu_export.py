import os
import sys
import json


class EnvUSDToGPUExport(object):

    def __init__(self, usd_path, output_dir=None):

        self.usd_path = usd_path
        self.output_dir = output_dir or os.path.dirname(usd_path)

        self._load_maya_plugin()
        print("__init__ done.")

    def _load_maya_plugin(self):
        """
        Load usd plugin in current session
        """
        import maya.cmds as cmds

        try:
            PLUGIN_NAMES = ["pxrUsd", "pxrUsdPreviewSurface", "gpuCache"]
            for plugin_name in PLUGIN_NAMES:
                cmds.loadPlugin(plugin_name, quiet=True)
        except Exception as e:
            print("Load plugin failed: ", e)

    def _import_usd(self):
        import maya.cmds as cmds
        cmds.file(
            self.usd_path,
            i=True,
            type="pxrUsdImport",
            options=";shadingMode=displayColor;readAnimData=0;useAsAnimationCache=0;assemblyRep=Collapsed;startTime=0;endTime=0;useCustomFrameRange=0"
        )

    def _export_gpu(self):
        import maya.cmds as cmds

        cmds.gpuCache(
            self.root_node,
            startTime=101,
            endTime=101,
            writeMaterials=True,
            dataFormat="ogawa",
            directory=self.output_dir,
            fileName="env_gpu.abc"
        )
        print("Output gpu to: {}".format(os.path.join(self.output_dir, "env_gpu.abc")))

    def _export_alembic(self):
        import maya.cmds as cmds

        output_path = os.path.join(self.output_dir, "env_alembic.abc")
        cmds.AbcExport(
            j="-frameRange 101 101 "
              "-stripNamespaces -worldSpace -writeVisibility -eulerFilter -dataFormat ogawa "
              "-root {root_node} "
              "-file {output_path}".format(output_path=output_path, root_node=self.root_node)
        )

    def export(self):
        self._import_usd()

        self.root_node = "|ROOT"

        self._export_gpu()
        self._export_alembic()

        print("Running GPU Export. mmmnnn 2255")

        # Bye


if __name__ == "__main__":
    auto_publish = EnvUSDToGPUExport()
    auto_publish.export()
