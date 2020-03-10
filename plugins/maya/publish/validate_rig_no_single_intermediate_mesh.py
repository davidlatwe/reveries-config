
import pyblish.api
from reveries.plugins import depended_plugins_succeed
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class ValidateNoSingleIntermediateMesh(pyblish.api.InstancePlugin):
    """Validate OutSet has no model that contains only intermediate mesh

    OutSet should not have any model that has only one shape and that shape is
    an intermediate object.

    """

    label = "No Single Intermediate Mesh"
    order = pyblish.api.ValidatorOrder + 0.12
    hosts = ["maya"]

    families = ["reveries.rig"]

    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidInstanceAction,
    ]

    dependencies = [
        "ValidateRigContents",
    ]

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise Exception("Single intermediate mesh found.")

    @classmethod
    def get_invalid(cls, instance):
        from maya import cmds

        invalid = list()

        if not depended_plugins_succeed(cls, instance):
            raise Exception("Depended plugin failed. See error log.")

        for out_set in instance.data["outSets"]:
            for node in cmds.ls(cmds.sets(out_set, query=True),
                                type="transform"):

                shapes = cmds.listRelatives(node, shapes=True, path=True)
                if (len(shapes) == 1 and
                        cmds.getAttr(shapes[0] + ".intermediateObject")):

                    invalid.append(node)

        return invalid
