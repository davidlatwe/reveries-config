import os
import sys
import json


class SetdressUSDToCacheExport(object):

    def __init__(self, usd_path, output_dir=None, root_node=None,
                 alembic=True, gpu=True):

        self.usd_path = usd_path
        self.output_dir = output_dir or os.path.dirname(usd_path)
        self.root_node = root_node or "|ROOT"
        self.alembic = alembic
        self.gpu = gpu

        self._load_maya_plugin()
        print("__init__ done.")

    def _load_maya_plugin(self):
        """
        Load usd plugin in current session
        """
        import maya.cmds as cmds

        try:
            PLUGIN_NAMES = ["pxrUsd", "pxrUsdPreviewSurface", "gpuCache", "AbcExport"]
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

        # Export GPU cache
        cmds.gpuCache(
            self.root_node,
            startTime=101,
            endTime=101,
            writeMaterials=True,
            dataFormat="ogawa",
            directory=self.output_dir,
            fileName="setdress_gpu"
        )

        # Export GPU ma
        ma_path = os.path.join(self.output_dir, "setdress_gpu.ma")
        self._wrap_gpu(ma_path, [("setdress_gpu.abc", "ROOT")])

        print("GPU path: {}".format(os.path.join(self.output_dir, "setdress_gpu.abc")))

    def _wrap_gpu(self, wrapper_path, gpu_files):
        """Wrapping GPU caches into a MayaAscii file

        (NOTE) The file path of `gpu_files` should be a relative path, relative to
            `wrapper_path`.

            For example:
                ```python

                wrapper_path = ".../publish/pointcache/v001/GPUCache/pointcache.ma"
                gpu_files = [("Peter_01/pointcache.abc", "Peter_01"), ...]

                ```

        Args:
            wrapper_path (str): MayaAscii file path
            gpu_files (list): A list of tuple of .abc file path and cached
                asset name.

        """
        MayaAscii_template = """//Maya ASCII scene
    requires maya "2016";
    requires -nodeType "gpuCache" "gpuCache" "1.0";
    """
        gpu_node_template = """
    $cachefile = `file -q -loc "{filePath}"`;  // Resolve relative path
    createNode transform -n "{nodeName}";
    createNode gpuCache -n "{nodeName}Shape" -p "{nodeName}";
        setAttr ".cfn" -type "string" $cachefile;
    """
        gpu_script = ""
        for gpu_path, node_name in gpu_files:
            gpu_path = gpu_path.replace("\\", "/")
            gpu_script += gpu_node_template.format(nodeName=node_name,
                                                   filePath=gpu_path)

        with open(wrapper_path, "w") as maya_file:
            maya_file.write(MayaAscii_template + gpu_script)

    def _export_alembic(self):
        import maya.cmds as cmds

        output_path = os.path.join(self.output_dir, "setdress_alembic.abc")
        cmds.AbcExport(
            j="-frameRange 101 101 "
              "-stripNamespaces -worldSpace -writeVisibility -eulerFilter -dataFormat ogawa "
              "-root {root_node} "
              "-file {output_path}".format(
                output_path=output_path,
                root_node=self.root_node
            )
        )

        print("Alembic path: {}".format(output_path))

    def export(self):
        self._import_usd()

        if self.alembic:
            self._export_alembic()

        if self.gpu:
            self._export_gpu()

        print("Running GPU Export Done.")

        # Bye


if __name__ == "__main__":
    usd_path = ''
    auto_publish = SetdressUSDToCacheExport(usd_path)
    auto_publish.export()
