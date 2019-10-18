
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
            raise Exception("No cacheable nodes in %s" % instance)
