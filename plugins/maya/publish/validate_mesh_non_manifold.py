from maya import cmds

import pyblish.api
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class ValidateMeshNonManifold(pyblish.api.Validator):
    """Ensure that meshes don't have non-manifold edges or vertices

    To debug the problem on the meshes you can use Maya's modeling
    tool: "Mesh > Cleanup..."

    """

    order = pyblish.api.ValidatorOrder + 0.3
    hosts = ["maya"]
    label = "Mesh Non-Manifold Vertices/Edges"
    families = [
        "reveries.model",
    ]
    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidInstanceAction,
    ]

    optional = True

    @staticmethod
    def get_invalid(instance):

        meshes = cmds.ls(instance, type="mesh", long=True, noIntermediate=True)

        invalid = []
        for mesh in meshes:
            if (cmds.polyInfo(mesh, nonManifoldVertices=True) or
                    cmds.polyInfo(mesh, nonManifoldEdges=True)):
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise ValueError("Meshes found with non-manifold "
                             "edges/vertices: {0}".format(invalid))
