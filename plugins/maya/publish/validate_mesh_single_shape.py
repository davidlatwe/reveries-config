import pyblish.api

from reveries.maya.plugins import MayaSelectInvalidAction


class ValidateMeshSingleShape(pyblish.api.InstancePlugin):
    """Transforms with a mesh must ever only contain a single mesh

    This ensures models only contain a single Non-Intermediate shape node.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.15
    hosts = ["maya"]
    label = "Mesh Single Shape"
    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidAction,
    ]

    @classmethod
    def get_invalid(cls, instance):

        from maya import cmds

        invalid = list()

        meshes = cmds.ls(instance, type="mesh", long=True)

        # get meshes transform
        transforms = cmds.listRelatives(meshes,
                                        parent=True,
                                        fullPath=True) or []

        for transform in transforms:
            shapes = cmds.listRelatives(transform,
                                        shapes=True,
                                        fullPath=True) or []
            non_intermediate = [s for s in shapes
                                if not cmds.getAttr(s + ".intermediateObject")]

            # Ensure the one child is a shape
            has_single_shape = len(non_intermediate) == 1

            if not has_single_shape:
                invalid.append(transform)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            self.log.error(
                "'%s' has transforms with multiple shapes:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Mesh Single Shape> Failed." % instance)

        self.log.info("%s <Mesh Single Shape> Passed." % instance)
