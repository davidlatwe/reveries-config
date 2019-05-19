
import pyblish.api
from maya import cmds


class CollectAtomsCrowdNodes(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect AtomsCrowd Nodes"
    hosts = ["maya"]
    families = [
        "reveries.atomscrowd",
        "reveries.imgseq",
    ]

    def process(self, instance):
        atoms_nodes = cmds.ls(type="tcAtomsNode")
        instance.data["AtomsNodes"] = atoms_nodes

        agent_groups = cmds.ls(instance, type="tcAgentGroupNode")
        instance.data["AtomsAgentGroups"] = agent_groups

        atoms_proxies = cmds.ls(instance, type="tcAtomsProxy")
        instance.data["AtomsProxies"] = atoms_proxies

        # For Rendering
        instance.data["hasAtomsCrowds"] = bool(atoms_proxies)
