import os
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
        from reveries.houdini import lib

        cache_root = instance.data["reprRoot"]
        assert cache_root is not None, ("Cache root not collected, "
                                        "this is a bug.")

        ropnode = instance[0]
        output = lib.get_output_parameter(ropnode).eval()

        try:
            os.path.relpath(output, cache_root)
        except ValueError as e:
            self.log.error(e)
            raise Exception("Please write output under %s" % cache_root)
