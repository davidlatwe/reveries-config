import pyblish.api
from avalon import io


class CollectFxLayerOutputs(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder + 0.49999
    label = "Collect Fx USD Outputs"
    hosts = ["houdini"]
    families = [
        "reveries.fx.layer_prim",
    ]

    def ins_exists(self, context, name):
        _exists = False
        for instance in context:
            if instance.data["subset"] == name:
                _exists = True
                break
        return _exists

    def process(self, instance):
        shot_name = instance.data['asset']

        _filter = {"type": "asset", "name": shot_name}
        asset_data = io.find_one(_filter)
        self.shot_id = asset_data['_id']

        # Create new instance
        context = instance.context
        backup = instance

        self._create_fxPrim(context, backup)
        self._create_finalPrim(context, backup)

    def _create_fxPrim(self, context, backup):
        name = "fxPrim"
        if not self.ins_exists(context, name):
            instance = context.create_instance(name)
            instance.data.update(backup.data)

            instance.data["family"] = "reveries.fx.usd"
            instance.data["subset"] = name
            instance.data["subsetGroup"] = "Fx"

            # === Set versionPin === #
            # self._check_version_pin(instance, name)

    def _create_finalPrim(self, context, backup):
        name = "finalPrim"
        if not self.ins_exists(context, name):
            instance = context.create_instance(name)
            instance.data.update(backup.data)

            instance.data["family"] = "reveries.final.usd"
            instance.data["subset"] = name

            # === Set versionPin === #
            self._check_version_pin(instance, name)

    def _check_version_pin(self, instance, subset_name):
        # Get subset id
        _filter = {
            "type": "subset",
            "parent": self.shot_id,
            "name": subset_name  # "camPrim"/"layPrim"/"finalPrim"
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
