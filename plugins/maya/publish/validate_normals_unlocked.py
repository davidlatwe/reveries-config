from maya import cmds

import pyblish.api
from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectInvalid(MayaSelectInvalidInstanceAction):

    label = "Select Locked"


class RepairInvalid(RepairInstanceAction):

    label = "Unlock"


class ValidateNormalsUnlocked(pyblish.api.Validator):
    """Validate all meshes in the instance have unlocked normals

    These can be unlocked manually through:
        Modeling > Mesh Display > Unlock Normals

    """

    order = pyblish.api.ValidatorOrder + 0.3
    hosts = ["maya"]
    families = ["reveries.model"]
    label = "Mesh Normals Unlocked"
    actions = [
        pyblish.api.Category("Select"),
        SelectInvalid,
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    optional = True

    @staticmethod
    def has_locked_normals(mesh):
        """Return whether a mesh node has locked normals"""
        return any(cmds.polyNormalPerVertex("{}.vtxFace[*][*]".format(mesh),
                                            query=True,
                                            freezeNormal=True))

    @classmethod
    def get_invalid(cls, instance):
        """Return the meshes with locked normals in instance"""

        meshes = cmds.ls(instance, type="mesh", long=True)
        return [mesh for mesh in meshes if cls.has_locked_normals(mesh)]

    def process(self, instance):
        """Raise invalid when any of the meshes have locked normals"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Meshes found with "
                             "locked normals: {0}".format(invalid))

    @classmethod
    def fix_invalid(cls, instance):
        """Unlocks all normals on the meshes in this instance."""
        invalid = cls.get_invalid(instance)
        for mesh in invalid:
            cmds.polyNormalPerVertex(mesh, unFreezeNormal=True)
            """
            # Smooth edge after unlock
            cmds.polySoftEdge(mesh,
                              constructionHistory=False,
                              angle=180)
            """
