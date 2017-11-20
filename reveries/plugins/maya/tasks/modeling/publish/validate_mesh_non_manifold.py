import pyblish.api
from maya import cmds
from reveries.maya import action


class ValidateMeshNonManifold(pyblish.api.Validator):
    """Ensure that meshes don't have non-manifold edges or vertices

    To debug the problem on the meshes you can use Maya's modeling
    tool: "Mesh > Cleanup..."

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.15
    actions = [action.SelectInvalidAction]
    hosts = ['maya']
    label = 'Mesh Non-Manifold'

    @staticmethod
    def get_invalid(instance):

        meshes = cmds.ls(instance, type='mesh', long=True)

        invalid = []
        for mesh in meshes:
            if (cmds.polyInfo(mesh, nonManifoldVertices=True) or
                    cmds.polyInfo(mesh, nonManifoldEdges=True)):
                invalid.append(mesh)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error(
                "'%s' Meshes found with non-manifold edges/vertices:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Mesh Non-Manifold> Failed." % instance)

        self.log.info("%s <Mesh Non-Manifold> Passed." % instance)
