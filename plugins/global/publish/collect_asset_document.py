
import pyblish.api
import avalon.api
import avalon.io


class CollectAssetDocument(pyblish.api.InstancePlugin):
    """Collect asset document from database

    keys in instance.data:
        * assetDoc

    """

    label = "Find Asset Document"
    order = pyblish.api.CollectorOrder + 0.3

    def process(self, instance):

        # Required environment variables
        ASSET = instance.data["asset"]

        project = instance.context.data["projectDoc"]

        asset = avalon.io.find_one({"type": "asset",
                                    "name": ASSET,
                                    "parent": project["_id"]})
        assert asset is not None, ("Could not find current asset '%s'" % ASSET)

        instance.data["assetDoc"] = asset
