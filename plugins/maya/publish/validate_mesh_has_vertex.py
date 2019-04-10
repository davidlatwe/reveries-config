
import pyblish.api

from reveries.maya.plugins import MayaSelectInvalidInstanceAction
from reveries.plugins import RepairInstanceAction


class RepairInvalid(RepairInstanceAction):

    label = "Delete No Vertex Meshes"


class ValidateMeshHasVertex(pyblish.api.InstancePlugin):
    """Validate meshes must has vertex"""

    order = pyblish.api.ValidatorOrder + 0.15
    label = "Mesh Has Vertex"
    hosts = ["maya"]
    families = [
        "reveries.model",
    ]
    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidInstanceAction,
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    optional = True

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        meshes = cmds.ls(instance, type="mesh", long=True)
        invalid = [mesh for mesh in meshes if
                   cmds.polyEvaluate(mesh, vertex=True) == 0]

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Meshes found with no vertex: "
                             "{0}".format(invalid))

    @classmethod
    def fix_invalid(cls, instance):
        from maya import cmds
        cmds.delete(cls.get_invalid(instance))
