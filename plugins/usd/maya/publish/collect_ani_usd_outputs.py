
import pyblish.api
from avalon import io


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

    def subset_exists(self, subset_name):
        filter = {"type": "subset",
                  "name": subset_name}
        subset_data = io.find_one(filter)

        return subset_data

    def process(self, instance):
        # Create new instance

        context = instance.context
        backup = instance

        # === Generate asset prim usd === #
        name = 'aniPrim'
        if not self.ins_exists(context, name):
            _family = "reveries.ani.ani_prim"

            _instance = context.create_instance(name)
            _instance.data.update(backup.data)

            _instance.data["family"] = _family
            _instance.data["families"] = [_family]
            _instance.data["subset"] = name
