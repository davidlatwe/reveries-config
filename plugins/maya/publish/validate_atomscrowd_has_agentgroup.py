
import pyblish.api


class ValidateAtomsCrowdHasAgentGroup(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate AgentGroup Exists"
    hosts = ["maya"]
    families = [
        "reveries.atomscrowd",
    ]

    def process(self, instance):
        assert instance.data["AgentGroups"], "No agentGroup node exists."
