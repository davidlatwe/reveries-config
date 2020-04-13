
import pyblish.api


class CollectAtomsCrowdNodes(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.CollectorOrder + 0.2
    label = "Collect AtomsCrowd Nodes"
    hosts = ["maya"]
    families = [
        "reveries.atomscrowd",
        "reveries.renderlayer",
    ]

    def process(self, instance):
        from maya import cmds

        atoms_nodes = cmds.ls(type="tcAtomsNode")
        instance.data["AtomsNodes"] = atoms_nodes

        agent_groups = cmds.ls(instance, type="tcAgentGroupNode")
        instance.data["AtomsAgentGroups"] = agent_groups

        atoms_proxies = cmds.ls(instance, type="tcAtomsProxy")
        instance.data["AtomsProxies"] = atoms_proxies

        # For Rendering
        instance.data["hasAtomsCrowds"] = bool(atoms_proxies)

        if atoms_nodes:
            self.log.info("AtomsNode collected.")

        if agent_groups:
            self.log.info("AgentGroupNode collected.")

        if atoms_proxies:
            self.log.info("AtomsProxy collected.")
            if "reveries.renderlayer" in instance.data["families"]:
                self.log.info("This renderLayer will be switched to "
                              "Deadline AtomsCrowd render group.")
