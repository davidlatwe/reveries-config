
import pyblish.api
import avalon.api
import avalon.io


class CollectAssetDocument(pyblish.api.ContextPlugin):
    """從資料庫讀取 Asset 文件"""

    """

    keys in context.data:
        * assetDoc

    """

    label = "取得 Asset 文件"
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
