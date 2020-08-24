
import pyblish.api
from avalon import io


class CollectAssetPrimUSDOutputs(pyblish.api.InstancePlugin):

    order = pyblish.api.CollectorOrder - 0.08
    label = "Collect assetPrim USD Outputs"
    hosts = ["maya"]
    families = [
        "reveries.look.asset_prim",
    ]

    def process(self, instance):
        asset_doc = instance.context.data["assetDoc"]

        # Get asset id
        asset_name = asset_doc["name"]
        _filter = {"type": "asset", "name": asset_name}
        asset_data = io.find_one(_filter)

        # Get subset id
        _filter = {
            "type": "subset",
            "parent": asset_data['_id'],
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
