import pyblish.api
from avalon import io


class CollectSetDressLayerOutputs(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder + 0.49999
    label = "Collect SetDress Outputs"
    hosts = ["houdini"]
    families = [
        "reveries.setdress.layer_prim",
    ]

    def ins_exists(self, context, name):
        _exists = False
        for instance in context:
            if instance.data["subset"] == name:
                _exists = True
                break
        return _exists

    def subset_exists(self, subset_name):
        _filter = {
            "type": "subset",
            "name": subset_name,
            "parent": self.shot_id
        }
        subset_data = io.find_one(_filter)
        return subset_data

    def process(self, instance):
        shot_name = instance.data['asset']

        _filter = {"type": "asset", "name": shot_name}
        asset_data = io.find_one(_filter)
        self.shot_id = asset_data['_id']

        # Create new instance
        context = instance.context
        backup = instance

        self._create_setdressPrim(context, backup)
        self._create_layPrim(context, backup)
        self._create_finalPrim(context, backup)

    def _create_setdressPrim(self, context, backup):
        # === Generate setdressPrim usd === #
        name = "setdressPrim"
        if not self.ins_exists(context, name):
            _instance = context.create_instance(name)
            _instance.data.update(backup.data)

            _instance.data["family"] = "reveries.setdress.usd"
            _instance.data["subset"] = name
            _instance.data["subsetGroup"] = "Layout"
            _instance.data["autoUpdate"] = True

    def _create_layPrim(self, context, backup):
        name = "layPrim"
        if not self.ins_exists(context, name):
            instance = context.create_instance(name)
            instance.data.update(backup.data)

            instance.data["family"] = "reveries.layout.usd"
            instance.data["subset"] = name
            instance.data["subsetGroup"] = "Layout"

            # === Set versionPin === #
            self._check_version_pin(instance, name)

    def _create_finalPrim(self, context, backup):
        name = "finalPrim"
        if not self.ins_exists(context, name):
            #  and not self.subset_exists(name)
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
