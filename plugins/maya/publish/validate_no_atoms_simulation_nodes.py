
import pyblish.api

from reveries import plugins
from reveries.maya import plugins as maya_plugins


class SelectAtomsSimNodes(maya_plugins.MayaSelectInvalidInstanceAction):

    label = "Select Atoms Sim Nodes"


class DeleteAtomsSimNodes(plugins.RepairInstanceAction):

    label = "Clean Up"


class ValidateNoAtomsSimulationNodes(pyblish.api.InstancePlugin):
    """
    """

    order = pyblish.api.ValidatorOrder
    label = "No Atoms Simulation Nodes"
    hosts = ["maya"]
    families = [
        "reveries.imgseq",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectAtomsSimNodes,
        pyblish.api.Category("Fix It"),
        DeleteAtomsSimNodes,
    ]

    @classmethod
    def get_invalid(cls, instance):
        invalid = list()

        invalid += instance.data["AtomsNodes"]
        invalid += instance.data["AtomsAgentGroups"]

        return invalid

    def process(self, instance):
        if not instance.data["deadlineEnable"]:
            # Allow local playblast simulation result.
            self.log.info("Not using Deadline, skip validation.")
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("Should not render with Atoms Simulation nodes.")

    @classmethod
    def fix_invalid(cls, instance):
        """Delete unknown nodes"""
        from maya import cmds

        for node in cls.get_invalid(instance):
            cmds.delete(node)
