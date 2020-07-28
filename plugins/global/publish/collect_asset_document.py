
import pyblish.api


class CollectAssetDocument(pyblish.api.ContextPlugin):
    """Collect asset document from database"""

    label = "Query Asset Document"
    order = pyblish.api.CollectorOrder + 0.499

    def process(self, context):
        from avalon import io

        project = context.data["projectDoc"]
        project_id = project["_id"]

        _cache = dict()
        _missing = False
        for instance in context:
            name = instance.data["asset"]

            if name in _cache:
                asset = _cache[name]
            else:
                asset = io.find_one({"type": "asset",
                                     "name": name,
                                     "parent": project_id})
                _cache[name] = asset

            if asset is None:
                self.log.error("Asset '%s' not exists in database." % name)
                _missing = True

            instance.data["assetDoc"] = asset

        if _missing:
            raise Exception("Asset not exists, see log.")
