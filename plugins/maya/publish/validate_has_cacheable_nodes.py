
import pyblish.api


class ValidateHasCacheableNodes(pyblish.api.InstancePlugin):

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Has Cacheable Nodes"

    families = [
        "reveries.pointcache",
    ]

    def process(self, instance):

        assert "outCache" in instance.data, "No 'outCache', this is a bug."

        if not instance.data["outCache"]:
            message = "No cacheable nodes in %s" % instance
            if instance.data.get("_hasHidden"):
                message += (", possibly hidden (only visible object can be "
                            "cached).")
            raise Exception(message)
