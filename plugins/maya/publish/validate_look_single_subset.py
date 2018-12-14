
import pyblish.api


class ValidateLookSingleSubset(pyblish.api.InstancePlugin):
    """Ensure one and only one model subset in look instance

    One look subset must pair to one and only one model subset, can not
    publish look on multiple subsets.

    """

    label = "Look On Single Subset"
    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    families = ["reveries.look"]

    def process(self, instance):
        paired = instance.data["paired_container"]

        if not len(paired):
            raise Exception("No model subset found.")

        if len(paired) > 1:
            raise Exception("One look instance can only pair to "
                            "one model subset.")
