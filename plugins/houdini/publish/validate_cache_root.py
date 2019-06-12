
import pyblish.api


class ValidateCacheRoot(pyblish.api.InstancePlugin):
    """Ensure cache storage root path collected
    """

    order = pyblish.api.ValidatorOrder - 0.1
    label = "Validate Cache Root"
    hosts = ["houdini"]
    families = [
        "reveries.vdbcache",
        "reveries.pointcache",
        "reveries.standin",
    ]

    def process(self, instance):
        cache_root = instance.data["reprRoot"]
        assert cache_root is not None, ("Cache root not collected, "
                                        "this is a bug.")
