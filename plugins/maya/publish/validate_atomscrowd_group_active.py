
import pyblish.api
from reveries.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Inactive AgentGroup"


class ValidateAtomsCrowdGroupActive(pyblish.api.InstancePlugin):
    """Ensure all AgentGroup is active (visible)
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate AgentGroup Active"
    hosts = ["maya"]
    families = [
        "reveries.atomscrowd",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
    ]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("Found inactive (hidden) AgentGroup.")

    @classmethod
    def get_invalid(cls, instance):
        from AtomsMaya.hostbridge.commands import MayaCommandsHostBridge

        invalid = list()

        for node in instance.data["AtomsAgentGroups"]:
            agent_group = MayaCommandsHostBridge.get_agent_group(node)
            if not agent_group.isActive():
                invalid.append(node)

        return invalid
