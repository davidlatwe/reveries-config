
import pyblish.api


class ValidateNoAtomsSimulationNodes(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ValidatorOrder
    label = "No Atoms Simulation Nodes"
    hosts = ["maya"]
    families = [
        "reveries.imgseq",
    ]

    def process(self, instance):
        if not instance.data["deadlineEnable"]:
            # Allow local playblast simulation result.
            self.log.info("Not using Deadline, skip validation.")
            return

        has_atoms = bool(instance.data["AtomsNodes"])
        has_group = bool(instance.data["AtomsAgentGroups"])

        message = "Should not render with Atoms Simulation nodes."
        assert not (has_atoms or has_group), message
