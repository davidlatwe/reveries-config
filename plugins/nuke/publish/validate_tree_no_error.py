
import pyblish.api


class ValidateTreeNoError(pyblish.api.InstancePlugin):
    """Validate node's input tree has no error"""

    label = "Validate Tree No Error"
    order = pyblish.api.ValidatorOrder
    hosts = ["nuke"]
    families = [
        "reveries.write",
    ]

    def process(self, instance):
        node = instance[0]

        if node.treeHasError():
            raise Exception("Input error found.")
