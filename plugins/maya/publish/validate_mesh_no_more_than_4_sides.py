
import pyblish.api
from reveries import plugins


class ValidateMeshNoMoreThan4Sides(pyblish.api.Validator):
    """Ensure that meshes don't have face that is more than 4 sides

    To debug the problem on the meshes you can use Maya's modeling
    tool: "Mesh > Cleanup..."

    """

    order = pyblish.api.ValidatorOrder + 0.3
    hosts = ["maya"]
    label = "Mesh Faces no more than 4 sides"
    families = [
        "reveries.model",
    ]
    actions = [
        pyblish.api.Category("Select"),
        plugins.MayaSelectInvalidInstanceAction,
    ]

    optional = True

    @staticmethod
    def get_invalid(instance):
        from maya import cmds
        from reveries.maya import lib

        meshes = cmds.ls(instance, type="mesh", long=True, noIntermediate=True)
        if not meshes:
            return list()

        # Get all faces
        faces = ["{0}.f[*]".format(node) for node in meshes]

        # Filter by constraint on edge length
        invalid = lib.polyConstraint(
            faces,
            mode=3,  # all items satisfying constraints are selected.
            type=0x0008,  # type=face
            size=3,  # nsided
        )

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Meshes found with face that is more than "
                             "4 sides: {0}".format(invalid))
