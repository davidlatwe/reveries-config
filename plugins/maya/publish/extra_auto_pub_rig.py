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
        import avalon

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

        # Get subset data
        filter = {"type": "subset", "parent": asset_doc["_id"]}
        subset_data = [subset for subset in avalon.io.find(filter)]

        subsets = [subset['name'] for subset in subset_data]
        if 'rigDefault' not in subsets:
            print('There is no rig publish, skip auto process.\n')
            return

        # Get latest rig version
        rig_subset = [subset for subset in subset_data if subset['name'] == 'rigDefault'][0]
        rig_subset_id = rig_subset['_id']

        # Submit subprocess
        mayapy_exe = os.path.join(os.path.dirname(sys.executable), 'mayapy.exe')
        cmd = [mayapy_exe, __file__,
               'asset_name={}'.format(str(asset_name)),
               'rig_subset_id={}'.format(str(rig_subset_id))]
        print('auto rig cmd: {}'.format(cmd))
        out_bytes = subprocess.check_output(cmd, shell=True)
        print(out_bytes)


class LauncherAutoPublish(object):
    def __init__(self):
        import maya.standalone as standalone
        standalone.initialize(name='python')

        self._init_args()
        self._publish()
        print('Auto publish rigging.')

    def _init_args(self):
        self.kargs = {}
        for _arg in sys.argv[1:]:
            _args_data = _arg.split('=')
            self.kargs[_args_data[0]] = _args_data[1]
        print('args: {}\n'.format(self.kargs))

        self.asset_name = self.kargs.get('asset_name', '')
        self.rig_subset_id = self.kargs.get('rig_subset_id', '')

    def _publish(self):
        import avalon
        import pyblish.util
        import maya.cmds as cmds

        # Switch task
        avalon.api.update_current_task(task='rigging', asset=self.asset_name)

        filter = {"type": "version", "parent": avalon.io.ObjectId(self.rig_subset_id)}
        latest_ver = avalon.io.find_one(filter, sort=[("name", -1)])
        rig_source = latest_ver['data']['source']

        # Get project root and rig source file
        _proj_root = avalon.Session.copy()['AVALON_PROJECTS']
        rig_source = str(rig_source.format(root=_proj_root)).replace('/', '\\')
        print('rig_source: {}. type: {}'.format(rig_source, type(rig_source)))

        # Open rig source file
        cmds.file(rig_source, open=True, force=True)

        # Update model
        host = avalon.api.registered_host()
        _container = list(host.ls())[0]
        avalon.pipeline.update(_container)
        print('Update model done.')

        # Save as file
        _tmp_dir = os.path.join(os.path.dirname(rig_source), 'tmp')
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

        # Fix AvalonUUID
        ValidateAvalonUUID = next(p for p in pyblish.api.discover()
                                  if p.__name__ == "ValidateAvalonUUID")
        context = pyblish.util.collect()
        instance = next(i for i in context if i.data["family"] == "reveries.rig")
        try:
            ValidateAvalonUUID.fix_invalid_missing(instance)
        except Exception as e:
            print('Fix uuid failed: {}.'.format(e))

        context = pyblish.util.collect()
        context.data["comment"] = 'Auto update model to latest version.'
        pyblish.util.validate(context)

        context = pyblish.util.collect()
        context.data["comment"] = 'Auto update model to latest version.'
        context = pyblish.util.validate(context=context)
        context = pyblish.util.extract(context=context)
        pyblish.util.integrate(context=context)


if __name__ == '__main__':
    LauncherAutoPublish()

