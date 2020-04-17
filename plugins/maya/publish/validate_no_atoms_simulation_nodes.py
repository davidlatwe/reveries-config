
import pyblish.api
from reveries import plugins


class SelectAtomsSimNodes(plugins.MayaSelectInvalidContextAction):

    label = "Select Atoms Sim Nodes"


class DeleteAtomsSimNodes(plugins.RepairContextAction):

    label = "Clean Up"


class ValidateNoAtomsSimulationNodes(pyblish.api.ContextPlugin):
    """
    """

    order = pyblish.api.ValidatorOrder
    label = "No Atoms Simulation Nodes"
    hosts = ["maya"]

    targets = ["deadline"]

    actions = [
        pyblish.api.Category("Select"),
        SelectAtomsSimNodes,
        pyblish.api.Category("Fix It"),
        DeleteAtomsSimNodes,
    ]

    @classmethod
    def get_invalid(cls, context):
        invalid = set()

        for instance in context:
            invalid.update(instance.data.get("AtomsNodes", []))
            invalid.update(instance.data.get("AtomsAgentGroups", []))

        return list(invalid)

    def process(self, context):
        invalid = self.get_invalid(context)
        if invalid:
            raise Exception("Should not publish with Atoms Simulation nodes "
                            "in Deadline.")

    @classmethod
    def fix_invalid(cls, context):
        """Delete unknown nodes"""
        from maya import cmds

        for node in cls.get_invalid(context):
            cmds.delete(node)
