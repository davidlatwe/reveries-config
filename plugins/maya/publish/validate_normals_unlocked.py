from maya import cmds

import pyblish.api
import reveries


class ValidateNormalsUnlocked(pyblish.api.Validator):
    """Validate all meshes in the instance have unlocked normals

    These can be unlocked manually through:
        Modeling > Mesh Display > Unlock Normals

    """

    order = pyblish.api.ValidatorOrder + 0.45
    hosts = ["maya"]
    families = ["reveries.model"]
    label = "Mesh Normals Unlocked"
    actions = [reveries.plugins.SelectInvalidAction,
               reveries.plugins.RepairInstanceAction]

    @staticmethod
    def has_locked_normals(mesh):
        """Return whether a mesh node has locked normals"""
        return any(cmds.polyNormalPerVertex("{}.vtxFace[*][*]".format(mesh),
                                            query=True,
                                            freezeNormal=True))

    @classmethod
    def get_invalid(cls, instance):
        """Return the meshes with locked normals in instance"""

        meshes = cmds.ls(instance, type='mesh', long=True)
        return [mesh for mesh in meshes if cls.has_locked_normals(mesh)]

    def process(self, instance):
        """Raise invalid when any of the meshes have locked normals"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Meshes found with "
                             "locked normals: {0}".format(invalid))

    @classmethod
    def fix(cls, instance):
        """Unlocks all normals on the meshes in this instance."""
        invalid = cls.get_invalid(instance)
        for mesh in invalid:
            cmds.polyNormalPerVertex(mesh, unFreezeNormal=True)
