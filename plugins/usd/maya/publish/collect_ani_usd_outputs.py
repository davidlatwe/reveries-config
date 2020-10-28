from avalon import io
import pyblish.api


class CollectAniUSDOutputs(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder
    label = "Collect Ani USD Outputs"
    hosts = ["maya"]
    families = [
        "reveries.pointcache.usd",
    ]

    def ins_exists(self, context, name):
        _exists = False
        for instance in context:
            if instance.data["subset"] == name:
                _exists = True
                break
        return _exists

    def process(self, instance):
        # Create new instance
        context = instance.context
        backup = instance

        # === Generate aniPrim usd === #
        name = 'aniPrim'
        if not self.ins_exists(context, name):
            _family = "reveries.ani.usd"

            _instance = context.create_instance(name)
            _instance.data.update(backup.data)

            _instance.data["family"] = _family
            _instance.data["families"] = [_family]
            _instance.data["subset"] = name

        # === Generate finalPrim usd === #
        name = 'finalPrim'
        if not self.ins_exists(context, name):
            _family = "reveries.final.usd"

            _instance = context.create_instance(name)
            _instance.data.update(backup.data)

            _instance.data["family"] = _family
            _instance.data["families"] = [_family]
            _instance.data["subset"] = name
            self._check_version_pin(_instance, name)

    def _check_version_pin(self, instance, subset_name):
        shot_name = instance.data['asset']
        _filter = {"type": "asset", "name": shot_name}
        shot_data = io.find_one(_filter)

        # Get subset id
        _filter = {
            "type": "subset",
            "parent": shot_data['_id'],
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
