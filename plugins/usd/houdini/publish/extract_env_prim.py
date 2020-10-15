import os
import sys
import json
import shutil
import traceback
import subprocess

import pyblish.api
from avalon import io, api


class ExtractEnvironment(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder + 0.21
    label = "Extract Environment USD Export"
    hosts = ["houdini"]
    families = [
        "reveries.env",
    ]

    def process(self, instance):
        import hou
        from reveries import utils
        from reveries.common.usd import update_reference_path

        auto_update = instance.data.get("autoUpdate", False)

        if auto_update:
            # Set comment
            context = instance.context
            context.data["comment"] = "Auto update"

            staging_dir = utils.stage_dir()
            filename = 'env_prim.usda'

            final_output = os.path.join(staging_dir, filename)
            tmp_file_path = self._copy_previous_file_to_tmp(staging_dir, instance).replace('\\', '/')

        else:
            ropnode = instance[0]

            # Get the filename from the filename parameter
            final_output = ropnode.evalParm("lopoutput")
            # Set custom staging dir
            staging_dir, filename = os.path.split(final_output)
            tmp_file_path = os.path.join(staging_dir, "env_prim_tmp.usda").replace('\\', '/')

            # Export temp usd file
            try:
                ropnode.parm("lopoutput").set(tmp_file_path)
                ropnode.render()
                ropnode.parm("lopoutput").set(final_output)

            except hou.Error as exc:
                traceback.print_exc()
                raise RuntimeError("Render failed: {0}".format(exc))

        # Set publish file name
        json_file_name = 'env.json'
        json_file_path = os.path.join(staging_dir, json_file_name)

        instance.data["repr.USD._stage"] = staging_dir
        instance.data["repr.USD._files"] = [filename, json_file_name]
        instance.data["repr.USD.entryFileName"] = filename
        # instance.data["step"] = "Layout"
        instance.data["subsetGroup"] = "Layout"
        instance.data["step_type"] = "env_prim"

        # Update reference/sublayer to latest version
        update_reference_path.update(usd_file=tmp_file_path, output_path=final_output)

        # Write json file
        self._write_json_file(usd_path=final_output, json_path=json_file_path)

        # Export Alembic Cache
        self.export_gpu_cache(final_output)

        # Export GPU Cache

        # Publish instance
        self._publish_instance(instance)

    def export_gpu_cache(self, final_output):
        print("\nExport GPU... ...")
        maya_path = r'C:\Program Files\Autodesk\Maya2020\bin'
        mayapy_exe = os.path.join(maya_path, "mayapy.exe")
        # py_file = r'F:\usd\test\usd_avalon\reveries-config\reveries\maya\usd\env_gpu_export.py'

        # cmd = [
        #     mayapy_exe,
        #     __file__,
        #     "usd_file={}".format(str(final_output)),
        # ]
        usdenv_bat = r'F:\usd\test\usd_avalon\reveries-config\plugins\usd\template\usdenvgpu_maya.bat'
        cmd = [usdenv_bat]

        out_bytes = subprocess.check_output(cmd, shell=True)
        # out, err = p.communicate()
        print("out: ", out_bytes)


        # print("Export gpu cmd: {}".format(cmd))
        # try:
        #     out_bytes = subprocess.check_output(cmd, shell=True)
        # except subprocess.CalledProcessError:
        #     print(out_bytes)
        #     # Mark failed for future debug.
        #     # io.update_many({"_id": model_version["_id"]},
        #     #                {"$set": {"data.rigAutoUpdateFailed": True}})
        #     raise Exception("Env gpu export failed.")
        # else:
        #     print(out_bytes)

    def _copy_previous_file_to_tmp(self, staging_dir, instance):
        from reveries.common import get_publish_files

        previous_subset_id = instance.data.get("previous_id", "")
        if not previous_subset_id:
            previous_subset_id = self.__get_previous_subset_id(instance)

        usd_file = get_publish_files.get_files(previous_subset_id, key='entryFileName').get('USD', '')
        if not usd_file:
            self.log.error("Missing usd file in publish folder")
            raise ValueError("Auto update subset {} failed.".format(instance.data["subset"]))

        # Copy previous usd file to tmp folder
        tmp_file_path = os.path.join(staging_dir, "env_prim_tmp.usda")
        try:
            shutil.copy2(usd_file, tmp_file_path)
        except OSError:
            msg = "An unexpected error occurred."
            print(msg)
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

        # publish_instance.run(instance)

        instance.data["published"] = True


class LauncherAutoEnvCacheExport(object):

    def __init__(self):
        kwargs = {}
        for _arg in sys.argv[1:]:
            _args_data = _arg.split("=")
            kwargs[_args_data[0]] = _args_data[1]

        self.usd_path = kwargs.get("usd_path", "").replace('\\', '/')
        print("usd_path: ", self.usd_path)
        self.contexts = list()

    def run(self):
        import maya.standalone as standalone
        from reveries.common.usd.pipeline.env_gpu_export import EnvUSDToGPUExport

        standalone.initialize(name="python")

        exporter = EnvUSDToGPUExport(self.usd_path)
        exporter.export()

        print("USD to ENV Done!!")

        standalone.uninitialize()
        # Bye


if __name__ == "__main__":
    auto_publish = LauncherAutoEncGPUExport()
    auto_publish.run()
