import os
import re
import sys
import subprocess

import pyblish.api


class ExtraAutoRig(pyblish.api.InstancePlugin):
    """Extract auto publish rig"""

    label = "Extract Auto Rig Publish"
    order = pyblish.api.IntegratorOrder + 0.499
    hosts = ["maya"]
    families = ["reveries.model"]

    def process(self, instance):
        from avalon import io
        import re

        asset_doc = instance.context.data['assetDoc']
        asset_name = asset_doc['name']

        # Check asset's rigging task option
        value_path = "task_options.rigging.autoModelUpdate.value"
        value = asset_doc["data"]
        for entry in value_path.split("."):
            value = value.get(entry, {})
        if not value:
            # Auto model update not enabled
            return

        model_subset, model_version, _ = instance.data["toDatabase"]

        if model_version["name"] == 1:
            # First version of model, must not have dependent rig
            return

        # Query previous version of model
        previous = io.find({"type": "version",
                            "parent": model_subset["_id"]},
                           sort=[("name", -1)],
                           projection={"_id": True},
                           skip=1)  # Get all previous versions of model
        previous = set([str(p["_id"]) for p in previous])
        if not previous:
            self.log.warning("Model is now on version %d but has no previous, "
                             "skip updating rig." % model_version["name"])
            return

        # Find dependent rig from previous model
        dependent_rigs = list()

        for rig_subset in io.find({"type": "subset",
                                   "parent": asset_doc["_id"],
                                   "name": re.compile("rig*")},
                                  projection={"_id": True}):

            latest_rig = io.find_one({"type": "version",
                                      "parent": rig_subset["_id"]},
                                     sort=[("name", -1)],
                                     projection={"data.dependencies": True})
            if latest_rig is None:
                # Not likely to happen, but just in case
                continue

            # Consider dependent if any dependency matched in model versions
            dependencies = set(latest_rig["data"]["dependencies"].keys())
            if dependencies.intersection(previous):
                dependent_rigs.append(str(latest_rig["_id"]))

        if not dependent_rigs:
            self.log.info("No rig to update, skip auto process.")
            return

        # Submit subprocess
        mayapy_exe = os.path.join(os.path.dirname(sys.executable),
                                  "mayapy.exe")
        cmd = [
            mayapy_exe,
            __file__,
            "asset_name={}".format(str(asset_name)),
            "rig_versions={}".format(",".join(dependent_rigs)),
        ]
        print("auto rig cmd: {}".format(cmd))
        try:
            out_bytes = subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError:
            # Mark failed
            io.update_many({"_id": model_version["_id"]},
                           {"$set": {"data.rigAutoUpdateFailed": True}})
            raise Exception("Model publish success but Rig auto update "
                            "failed. Please inform rigger or TD.")
        else:
            print(out_bytes)


class LauncherAutoPublish(object):
    def __init__(self):
        kwargs = {}
        for _arg in sys.argv[1:]:
            _args_data = _arg.split("=")
            kwargs[_args_data[0]] = _args_data[1]

        self.asset_name = kwargs.get("asset_name", "")
        self.rig_versions = kwargs.get("rig_versions", "").split(",")
        self.contexts = list()

    def run(self):
        import maya.standalone as standalone
        import pyblish.util

        standalone.initialize(name='python')

        print('Auto publish rigging.')
        for rig_version in self.rig_versions:
            self._publish(rig_version)

        # Integrate all updated rigs if all extraction succeed
        for context in self.contexts:
            context.data["_autoPublishingSkipUnlock"] = True
            pyblish.util.integrate(context=context)

        standalone.uninitialize()

    def _publish(self, rig_version):
        from avalon import api, io
        import pyblish.util
        import maya.cmds as cmds

        # Switch task
        api.update_current_task(task='rigging', asset=self.asset_name)

        version_id = io.ObjectId(rig_version)
        latest_ver = io.find_one({"type": "version", "_id": version_id})
        rig_source = latest_ver['data']['source']

        # Get project root and rig source file
        _proj_root = api.Session.copy()['AVALON_PROJECTS']
        rig_source = str(rig_source.format(root=_proj_root)).replace('/', '\\')
        print('rig_source: {}. type: {}'.format(rig_source, type(rig_source)))

        # Open rig source file
        cmds.file(rig_source, open=True, force=True)

        # Update model
        host = api.registered_host()
        _container = list(host.ls())[0]
        api.update(_container)
        print('Update model done.')

        # Save as file
        _tmp_dir = os.path.join(os.path.dirname(rig_source), "_auto_update")
        if not os.path.exists(_tmp_dir):
            os.mkdir(_tmp_dir)
            os.chmod(_tmp_dir, 777)

        _source_file = (os.path.splitext(os.path.basename(rig_source)))
        if 'auto_model_update' not in _source_file[0]:
            _new_file_name = '{}.auto_model_update.001{}'.format(_source_file[0], _source_file[1])
        else:
            # _new_file_name = r'rigging_v0001.published.auto_model_update.001.published.mb'
            current_v = re.findall('.auto_model_update.(\d+).', rig_source)[0]
            new_v = '{:03d}'.format(int(current_v) + 1)
            _new_file_name = '{}{}'.format(_source_file[0],
                                           _source_file[1]).replace('.{}.published.'.format(current_v),
                                                                    '.{}.'.format(new_v))
        _save_to = os.path.join(_tmp_dir, _new_file_name)
        cmds.file(rename=_save_to)
        cmds.file(force=True, save=True)
        print('Save to : {}'.format(_save_to))

        # Publish
        pyblish.api.register_target('localhost')

        # Fix AvalonUUID before validate
        ValidateAvalonUUID = next(p for p in pyblish.api.discover()
                                  if p.__name__ == "ValidateAvalonUUID")
        for instance in pyblish.util.collect():
            try:
                ValidateAvalonUUID.fix_invalid_missing(instance)
            except Exception as e:
                print('Fix uuid failed: {}.'.format(e))

        context = pyblish.util.collect()
        context.data["comment"] = "Auto update model to latest version."
        context = pyblish.util.validate(context=context)
        context = pyblish.util.extract(context=context)

        if not all(result["success"] for result in context.data["results"]):
            raise RuntimeError("Atomicity not held, aborting.")

        self.contexts.append(context)


if __name__ == '__main__':
    auto_publish = LauncherAutoPublish()
    auto_publish.run()

