
import pyblish.api

from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class ValidateModelContent(pyblish.api.InstancePlugin):
    """Adheres to the content of 'model' family

    - Must only contain: transforms, meshes and groups
    - At least one mesh

    So if there are nurbs or curves or any other node that is not
    mesh nor sub-group under *ROOT* group, this validation fails.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.1
    hosts = ["maya"]
    label = "Model Content"
    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidInstanceAction,
    ]

    @classmethod
    def get_invalid(cls, instance):

        from maya import cmds

        invalid = list()

        # Ensure only valid node types
        allowed = ("mesh", "transform", "nurbsCurve")
        nodes = cmds.ls(instance, long=True)
        valid = cmds.ls(instance, long=True, type=allowed)
        invalid = set(nodes) - set(valid)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error("These nodes are not allowed: %s" % invalid)
            raise Exception("%s <Model Content> Failed." % instance)

        self.log.info("%s <Model Content> Passed." % instance)
