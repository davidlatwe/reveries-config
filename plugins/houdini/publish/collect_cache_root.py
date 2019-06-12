
import os
import pyblish.api


class CollectCacheRoot(pyblish.api.InstancePlugin):
    """Inject cache storage root path into instance"""

    order = pyblish.api.CollectorOrder
    label = "Root Path For Cache"
    hosts = ["houdini"]
    families = [
        "reveries.vdbcache",
        "reveries.pointcache",
        "reveries.standin",
    ]

    def process(self, instance):
        instance.data["reprRoot"] = os.getenv("AVALON_CACHE_ROOT")
