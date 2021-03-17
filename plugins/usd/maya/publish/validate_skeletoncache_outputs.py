import pyblish.api


class ValidateSkeletonCacheOutputs(pyblish.api.InstancePlugin):
    """Check shape name are same with model publish.
    """

    label = "Validate Skeletoncache"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]

    families = ["reveries.skeletoncache"]

    def process(self, instance):
        root_node = instance.data.get("root_node", "")
        rig_subset_id = instance.data("rig_subset_id", "")
        print("root_node: ", instance, root_node, rig_subset_id)
