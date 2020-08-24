import os
import json

import pyblish.api
from avalon import io, api


class CollectSetDressLayerOutputs(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder + 0.49999
    label = "Collect SetDress Outputs"
    hosts = ["houdini"]
    families = [
        "reveries.setdress.layer_prim",
        "reveries.setdress.usd"
    ]

    def ins_exists(self, context, name):
        _exists = False
        for instance in context:
            if instance.data["subset"] == name:
                _exists = True
                break
        return _exists

    def subset_exists(self, subset_name):
        _filter = {"type": "subset",
                  "name": subset_name,
                  "parent": self.shot_id}
        subset_data = io.find_one(_filter)
        return subset_data

    def _get_all_setdressPrim_subset(self):
        _filter = {
            "type": "subset",
            "step_type": 'setdress_prim',
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
        if _family == "reveries.setdress.layer_prim":
            created = self._create_setdressPrim_subset(
                context,
                backup,
                layer_instance=instance
            )
            self._create_layPrim(context, backup, force=created)
        elif _family == "reveries.setdress.usd":
            self._create_layPrim(context, backup, force=True)

    def _create_setdressPrim_subset(self, context, backup, layer_instance=None):
        _create = False
        all_setdress_subset_data = self._get_all_setdressPrim_subset()
        for setdress_subset_data in all_setdress_subset_data:
            if self.__need_autoUpdate(layer_instance, setdress_subset_data):
                # === Generate setdress prim usd === #
                # name = "setdressDefault"
                name = setdress_subset_data["name"]

                if not self.ins_exists(context, name):
                    _instance = context.create_instance(name)
                    _instance.data.update(backup.data)

                    _instance.data["family"] = "reveries.setdress.usd"
                    _instance.data["subset"] = name
                    _instance.data["subsetGroup"] = "Layout"
                    _instance.data["autoUpdate"] = True
                    _instance.data["previous_id"] = setdress_subset_data["_id"]

                    _create = True

        return _create

    def __need_autoUpdate(self, layer_instance, setdress_subset_data):
        """
        Auto update when previous setdressPrim's subset
        version has this layer inside.
        :return:
        """
        from reveries.common import get_publish_files

        # Get publish file from subset id
        setdress_subset_id = setdress_subset_data["_id"]
        file = get_publish_files.get_files(
            setdress_subset_id,
            key='entryFileName').get('USD', '')
        if not file:
            return False

        # Get json file path
        publish_dir = os.path.dirname(file)
        json_path = os.path.join(publish_dir, 'setdress.json')
        if not os.path.exists(json_path):
            return False

        # Check layer name in json file
        with open(json_path) as json_file:
            setdress_data = json.load(json_file)

        if not setdress_data:
            return False

        layer_subset_name = layer_instance.data["subset"]
        if layer_subset_name in list(setdress_data.get("Shot", {}).keys()):
            return True

        return False

    def _create_layPrim(self, context, backup, force=False):
        def __create():
            name = "layPrim"
            if not self.ins_exists(context, name):
                instance = context.create_instance(name)
                instance.data.update(backup.data)

                instance.data["family"] = "reveries.layout.usd"
                instance.data["subset"] = "layPrim"
                instance.data["subsetGroup"] = "Layout"

                # === Set versionPin === #
                # Get subset id
                _filter = {
                    "type": "subset",
                    "parent": self.shot_id,
                    "name": name
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

        if force:
            __create()
            return
