import avalon

import pyblish.api


class ValidateModelHasUSDPublished(pyblish.api.InstancePlugin):
    """Validate asset already published usd."""

    order = pyblish.api.ValidatorOrder + 0.491

    label = "Validate Model USD Published"
    hosts = ["maya"]
    families = [
        "reveries.pointcache.usd",
        "reveries.pointcache.child.usd"
    ]

    def process(self, instance):
        from reveries.maya import pipeline

        if instance.data.get("isDummy"):
            return

        asset_id = instance.data.get("asset_id", "")
        asset_name = instance.data.get("asset_name", "")
        if not asset_id or not asset_id:
            raise Exception("Get asset id/name failed.")
        # instance.data["asset_name"] = asset_name

        # Check asset already publish USD geom.usd
        geom_exists = self._check_model_geom_exists(asset_id)
        if not geom_exists:
            raise Exception("{}: No model USD published:<br>"
                            "Asset: {}<br>"
                            "ID: {}".format(
                instance, asset_name, asset_id))

    def _check_model_geom_exists(self, asset_id):
        from reveries.common import get_publish_files

        # Get asset prim usd file
        _filter = {
            "type": "subset",
            "name": "assetPrim",
            "parent": avalon.io.ObjectId(asset_id)
        }
        assetprim_data = avalon.io.find_one(_filter)
        if not assetprim_data:
            return False

        asset_prim_usd_files = get_publish_files.get_files(
            assetprim_data['_id']).get('USD', [])

        return asset_prim_usd_files

