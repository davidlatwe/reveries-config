
import pyblish.api
from avalon import io


class CollectLookDevUSDOutputs(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder - 0.09
    label = "Collect lookDev USD Outputs"
    hosts = ["maya"]
    families = [
        "reveries.look",
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
                   "parent": self.asset_id}
        subset_data = io.find_one(_filter)
        return subset_data

    def proxy_prim_exists(self):
        _filter = {"type": "subset",
                   "name": 'proxyPrim',
                   "parent": self.asset_id}
        subset_data = io.find_one(_filter)
        return subset_data

    def process(self, instance):
        from reveries.common import skip_instance

        asset_name = instance.data['asset']
        context = instance.context

        if skip_instance(context, ['reveries.xgen']):
            return

        _filter = {"type": "asset", "name": asset_name}
        asset_data = io.find_one(_filter)
        self.asset_id = asset_data['_id']

        # Create new instance
        context = instance.context
        backup = instance

        # === Generate asset pre prim usd === #
        # Check subset type
        subset_types = []
        if 'proxy' in instance.data["subset"].lower():
            subset_types.append('proxy')
        else:
            # If new look variant, need to update proxy_prim
            subset_name = instance.data["subset"]
            if not self.subset_exists(subset_name) and self.proxy_prim_exists():
                subset_types.append('proxy')

            subset_types.append('render')

        for subset_type in subset_types:
            name = '{}Prim'.format(subset_type)
            if not self.ins_exists(context, name):
                instance = context.create_instance(name)
                instance.data.update(backup.data)

                instance.data["family"] = "reveries.look.pre_prim"
                instance.data["subset"] = name
                instance.data["subset_type"] = subset_type
                instance.data["subsetGroup"] = "USD"

        # === Generate asset prim usd === #
        name = 'assetPrim'
        if not self.ins_exists(context, name):
            instance = context.create_instance(name)
            instance.data.update(backup.data)

            instance.data["family"] = "reveries.look.asset_prim"
            instance.data["subset"] = name
