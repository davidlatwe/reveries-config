
import pyblish.api
from avalon import io


class CollectMODUSDOutputs(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder - 0.09
    label = "Collect MOD USD Outputs"
    hosts = ["maya"]
    families = [
        "reveries.model",
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
                  "parent": self.asset_id}
        subset_data = io.find_one(filter)
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

        # Create proxyPrim/renderPrim when only publish model
        # if these 2 subset already published.
        if len(context) != 1:
            return

        # === Generate asset pre prim usd === #
        # Check subset type
        subset_types = []

        if self.subset_exists('proxyPrim'):
            subset_types.append('proxy')

        if self.subset_exists('renderPrim'):
            subset_types.append('render')

        if subset_types:
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

