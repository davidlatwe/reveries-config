
import pyblish.api


class ValidateLookHasAssigned(pyblish.api.InstancePlugin):
    """Ensure model subset in look instance

    One look subset must atleast pairing to one model subset, can not
    publish look without any assigned subsets.

    """

    label = "Has Assigned Subset"
    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    families = ["reveries.look"]

    def process(self, instance):
        if not len(instance.data["pairedContainers"]):
            raise Exception("No model subset found, this is a bug.")
