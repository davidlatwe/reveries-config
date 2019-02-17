
import pyblish.api
import avalon.api
import avalon.io


class CollectAssetDocument(pyblish.api.ContextPlugin):
    """Collect asset document from database

    keys in context.data:
        * assetDoc

    """

    label = "Find Asset Document"
    order = pyblish.api.CollectorOrder - 0.34

    def process(self, context):

        # Required environment variables
        ASSET = avalon.api.Session["AVALON_ASSET"]

        project = context.data["projectDoc"]

        asset = avalon.io.find_one({"type": "asset",
                                    "name": ASSET,
                                    "parent": project["_id"]})
        assert asset is not None, ("Could not find current asset '%s'" % ASSET)

        context.data["assetDoc"] = asset
