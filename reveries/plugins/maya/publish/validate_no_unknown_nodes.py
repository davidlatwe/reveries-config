import pyblish.api
from reveries.maya import action


class ValidateNoUnknownNodes(pyblish.api.InstancePlugin):
    """Checks to see if there are any unknown nodes in the instance.

    This often happens if nodes from plug-ins are used but are not available
    on this machine.

    Note: Some studios use unknown nodes to store data on (as attributes)
        because it's a lightweight node.

    validate instance.data:
        unknown_nodes

    """

    order = pyblish.api.ValidatorOrder - 0.01
    actions = [action.SelectInvalidAction]
    hosts = ['maya']
    label = "No Unknown Nodes"

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)
        if invalid:
            self.log.warning("Unknown nodes found: {0}".format(invalid))
            self.log.warning("<No Unknown Nodes> Warned.")
        else:
            self.log.info("%s <No Unknown Nodes> Passed." % instance)

    @staticmethod
    def get_invalid(instance):
        return instance.data["unknown_nodes"]
