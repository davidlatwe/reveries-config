import os
import sys
import json
import shutil
import subprocess

import pyblish.api
from avalon import io


class ExtractSetDress(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.21
    label = "Extract SetDress USD Export"
    hosts = ["houdini"]
    families = [
        "reveries.setdress.usd",
    ]

    def process(self, instance):
        from reveries import utils
        from reveries.common.usd.pipeline import setdress_prim_export

        # Set comment
        context = instance.context
        context.data["comment"] = "Auto update"
        # subset_name = instance.data["subset"]

        staging_dir = utils.stage_dir()
        filename = 'setdress_prim.usda'

        final_output = os.path.join(staging_dir, filename)

        #
        json_file_name = 'setdress.json'
        json_file_path = os.path.join(staging_dir, json_file_name)

        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [filename, json_file_name]
        instance.data["repr.USD.entryFileName"] = filename

        instance.data["subsetGroup"] = "Layout"

        # Export setdressPrim
        shot_name = instance.data['asset']
        setdress_prim_export.SetDressPrimExport.export(final_output, shot_name)

        # Write json file
        self._write_json_file(usd_path=final_output, json_path=json_file_path)

        # ==== Export GPU/Alembic Cache ==== #
        self._export_gpu_cache(final_output)

        # Set GPU file name
        gpu_file_name = 'setdress_gpu.abc'
        gpu_file_path = os.path.join(staging_dir, gpu_file_name)

        gpu_ma_file_name = 'setdress_gpu.ma'
        gpu_ma_file_path = os.path.join(staging_dir, gpu_ma_file_name)

        if os.path.exists(gpu_file_path) and os.path.exists(gpu_ma_file_path):
            instance.data["repr.GPUCache._stage"] = staging_dir
            instance.data["repr.GPUCache._files"] = [
                gpu_ma_file_name,
                gpu_file_name
            ]  # _hardlinks
            instance.data["repr.GPUCache.entryFileName"] = gpu_ma_file_name
        else:
            self.log.info("Setdressing gpu cahce export failed.")

        # Set Alembic file name
        alembic_file_name = 'setdress_alembic.abc'
        alembic_file_path = os.path.join(staging_dir, alembic_file_name)

        if os.path.exists(alembic_file_path):
            instance.data["repr.Alembic._stage"] = staging_dir
            instance.data["repr.Alembic._files"] = [alembic_file_name]
            instance.data["repr.Alembic.entryFileName"] = alembic_file_name
        else:
            self.log.info("Setdressing alembic cahce export failed.")

        # ==== Publish instance ==== #
        self._publish_instance(instance)

    def _export_gpu_cache(self, usd_file):
        usdenv_bat = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..\\..\\..\\usd\\template\\usdToCache.bat"
            )
        )
        cmd = [usdenv_bat, __file__, usd_file]

        try:
            out_bytes = subprocess.check_output(cmd, shell=True)
            self.log.info("out: {}".format(out_bytes))
        except Exception as e:
            self.log.info("Export GPU/Alembic cache failed: {}".format(e))

    def _copy_previous_file_to_tmp(self, staging_dir, instance):
        from reveries.common import get_publish_files

        previous_subset_id = instance.data.get("previous_id", "")
        if not previous_subset_id:
            previous_subset_id = self.__get_previous_subset_id(instance)

        usd_file = get_publish_files.get_files(
            previous_subset_id, key='entryFileName').get('USD', '')
        if not usd_file:
            self.log.error("Missing usd file in publish folder")
            raise ValueError(
                "Auto update subset {} failed.".format(instance.data["subset"]))

        # Copy previous usd file to tmp folder
        tmp_file_path = os.path.join(staging_dir, "setdress_prim_tmp.usda")
        try:
            shutil.copy2(usd_file, tmp_file_path)
        except OSError:
            msg = "An unexpected error occurred."
            self.log.info(msg)
            raise OSError(msg)

        return tmp_file_path

    def __get_previous_subset_id(self, instance):
        # Get shot id
        shot_name = instance.data['asset']

        _filter = {"type": "asset", "name": shot_name}
        asset_data = io.find_one(_filter)
        shot_id = asset_data['_id']

        # Get subset data
        subset_name = instance.data["subset"]
        _filter = {
            "type": "subset",
            "name": subset_name,
            "parent": shot_id
        }
        subset_data = io.find_one(_filter)

        return subset_data["_id"]

    def _write_json_file(self, usd_path=None, json_path=None):
        from reveries.common.usd.get_asset_info import GetAssetInfo

        asset_obj = GetAssetInfo(usd_file=usd_path)
        asset_info_data = asset_obj.asset_info

        with open(json_path, 'w') as f:
            json.dump(asset_info_data, f, ensure_ascii=False, indent=4)

    def _publish_instance(self, instance):
        # === Publish instance === #
        from reveries.common.publish import publish_instance

        publish_instance.run(instance)

        instance.data["_preflighted"] = True


class LauncherAutoEnvCacheExport(object):

    def __init__(self):
        kwargs = {}
        for _arg in sys.argv[1:]:
            _args_data = _arg.split("=")
            kwargs[_args_data[0]] = _args_data[1]

        self.usd_path = kwargs.get("usd_path", "").replace('\\', '/')
        self.contexts = list()

    def run(self):
        import maya.standalone as standalone
        from reveries.common.usd.pipeline.\
            setdress_cache_export import SetdressUSDToCacheExport

        standalone.initialize(name="python")
        try:
            exporter = SetdressUSDToCacheExport(self.usd_path)
            exporter.export()

            print("USD to ENV Done!!")
        except Exception as e:
            print("USD to ENV Failed: {}".format(e))

        standalone.uninitialize()
        # Bye


if __name__ == "__main__":
    auto_publish = LauncherAutoEnvCacheExport()
    auto_publish.run()
