import pyblish.api
from maya import cmds
from reveries.maya import action


class ValidateMeshLaminaFaces(pyblish.api.InstancePlugin):
    """Validate meshes don't have lamina faces.

    Lamina faces share all of their edges.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.15
    actions = [action.SelectInvalidAction]
    hosts = ['maya']
    label = 'Mesh Lamina Faces'

    @staticmethod
    def get_invalid(instance):
        meshes = cmds.ls(instance, type='mesh', long=True)
        invalid = [mesh for mesh in meshes if
                   cmds.polyInfo(mesh, laminaFaces=True)]

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance 'objectSet'"""

        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error(
                "'%s' Meshes found with lamina faces:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Mesh Lamina Faces> Failed." % instance)

        self.log.info("%s <Mesh Lamina Faces> Passed." % instance)
