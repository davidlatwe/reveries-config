from avalon import io
import pyblish.api


class CollectRigPrimOutputs(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder + 0.25
    label = "Collect Rig Prim USD Outputs"
    hosts = ["maya"]
    families = [
        "reveries.rig"
    ]

    def ins_exists(self, context, name):
        _exists = False
        for instance in context:
            if instance.data["subset"] == name:
                _exists = True
                break
        return _exists

    def process(self, instance):
        if not instance.data.get("publishUSD", False):
            return

        subset_name = instance.data["subset"]

        # Create new instance
        context = instance.context
        backup = instance

        # === Generate rigPrim usd === #
        name = '{}Skeleton'.format(subset_name)
        if not self.ins_exists(context, name):
            _family = "reveries.rig.skeleton"

            _instance = context.create_instance(name)
            _instance.data.update(backup.data)

            _instance.data["family"] = _family
            _instance.data["families"] = [_family]
            _instance.data["subset"] = name
            _instance.data["subsetGroup"] = "USD"

        # === Generate rigPrim usd === #
        name = '{}Prim'.format(subset_name)
        if not self.ins_exists(context, name):
            _family = "reveries.rig.usd"

            _instance = context.create_instance(name)
            _instance.data.update(backup.data)

            _instance.data["family"] = _family
            _instance.data["families"] = [_family]
            _instance.data["subset"] = name
            self._check_version_pin(_instance, name)

    def _check_version_pin(self, instance, subset_name):
        shot_name = instance.data['asset']
        _filter = {"type": "asset", "name": shot_name}
        asset_data = io.find_one(_filter)

        # Get subset id
        _filter = {
            "type": "subset",
            "parent": asset_data['_id'],
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
