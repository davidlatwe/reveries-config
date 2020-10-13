import os
import json

import pyblish.api
from avalon import io, api


class CollectEnvironmentLayerOutputs(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder + 0.49999
    label = "Collect Environment Outputs"
    hosts = ["houdini"]
    families = [
        "reveries.env.layer",
        "reveries.env"
    ]

    def ins_exists(self, context, name):
        _exists = False
        for instance in context:
            if instance.data["subset"] == name:
                _exists = True
                break
        return _exists

    def subset_exists(self, subset_name):
        filter = {"type": "subset",
                  "name": subset_name,
                  "parent": self.shot_id}
        subset_data = io.find_one(filter)
        return subset_data

    def _get_all_envPrim_subset(self):
        _filter = {
            "type": "subset",
            "step_type": 'env_prim',
            "parent": self.shot_id
        }
        return [s for s in io.find(_filter)]

    def process(self, instance):
        shot_name = instance.data['asset']

        _filter = {"type": "asset", "name": shot_name}
        asset_data = io.find_one(_filter)
        self.shot_id = asset_data['_id']

        # Create new instance
        context = instance.context
        backup = instance

        _family = instance.data["family"]
        if len(context) == 1 and _family == "reveries.env.layer":
            print('1111')
            self._create_envPrim_subset(context, backup, layer_instance=instance)
            self._create_layPrim(context, backup)
        elif len(context) == 1 and _family == "reveries.env":
            print('222222')
            self._create_layPrim(context, backup)
        else:
            print('333333')
            self._create_layPrim(context, backup)

    def _create_envPrim_subset(self, context, backup, layer_instance=None):
        all_env_subset_data = self._get_all_envPrim_subset()
        for env_subset_data in all_env_subset_data:
            if self.__need_autoUpdate(layer_instance, env_subset_data):
                # === Generate env prim usd === #
                # name = "envDefault"
                name = env_subset_data["name"]

                if not self.ins_exists(context, name):
                    env_instance = context.create_instance(name)
                    env_instance.data.update(backup.data)

                    env_instance.data["family"] = "reveries.env"
                    env_instance.data["subset"] = name
                    env_instance.data["subsetGroup"] = "Layout"
                    env_instance.data["autoUpdate"] = True
                    env_instance.data["previous_id"] = env_subset_data["_id"]

        # TODO: Support different subset name of env_prim.usd

    def __need_autoUpdate(self, layer_instance, env_subset_data):
        """
        Auto update when previous envPrim's subset version has this layer inside.
        :return:
        """
        from reveries.common import get_publish_files

        # Get publish file from subset id
        env_subset_id = env_subset_data["_id"]
        file = get_publish_files.get_files(env_subset_id, key='entryFileName').get('USD', '')
        if not file:
            return False

        # Get json file path
        publish_dir = os.path.dirname(file)
        json_path = os.path.join(publish_dir, 'env.json')
        if not os.path.exists(json_path):
            return False

        # Check layer name in json file
        with open(json_path) as json_file:
            env_data = json.load(json_file)

        if not env_data:
            return False

        layer_subset_name = layer_instance.data["subset"]
        if layer_subset_name in list(env_data.get("Shot", {}).keys()):
            return True

        return False

    def _create_layPrim(self, context, backup):
        return

        # === Generate asset prim usd === #
        if self.ins_exists(context, "envDefault"):
            name = "layPrim"
            if not self.ins_exists(context, name):
                instance = context.create_instance(name)
                instance.data.update(backup.data)

                instance.data["family"] = "reveries.layout"
                instance.data["subset"] = "layPrim"
                instance.data["subsetGroup"] = "Layout"

                # === Set versionPin === #
                # Get subset id
                _filter = {
                    "type": "subset",
                    "parent": self.shot_id,
                    "name": "assetPrim"
                }
                subset_data = io.find_one(_filter)
                if subset_data:
                    # Get version name
                    _filter = {
                        "type": "version",
                        "parent": subset_data['_id'],
                    }
                    version_data = io.find_one(_filter, sort=[("name", -1)])
                    if version_data:
                        instance.data["versionPin"] = version_data["name"]
