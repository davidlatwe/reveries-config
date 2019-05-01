
import pyblish.api
from maya import cmds


class CollectAtomsCrowdAgentGroup(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect AtomsCrowd AgentGroup"
    hosts = ["maya"]
    families = [
        "reveries.atomscrowd",
    ]

    def process(self, instance):
        agent_groups = cmds.ls(instance, type="tcAgentGroupNode")
        instance.data["AgentGroups"] = agent_groups
