import pyblish.api
from maya import cmds


class ValidateMeshSingleShape(pyblish.api.InstancePlugin):
    """Transforms with a mesh must ever only contain a single mesh

    This ensures models only contain a single shape node.

    """

    families = ["reveries.model"]
    order = pyblish.api.ValidatorOrder + 0.15
    hosts = ["maya"]
    label = "Mesh Single Shape"

    def process(self, instance):

        assert instance.data.get("meshes", None), (
            "Instance has no meshes!")

        invalid = list()

        # get meshes transform
        transforms = cmds.listRelatives(instance.data['meshes'], parent=True)

        for transform in set(transforms):
            shapes = cmds.listRelatives(transform, shapes=True) or list()

            # Ensure the one child is a shape
            has_single_shape = len(shapes) == 1
            self.log.debug("%s has single shape: %s" % (
                transform, has_single_shape))

            # Ensure the one shape is of type "mesh"
            has_single_mesh = (
                has_single_shape and
                cmds.nodeType(shapes[0]) == "mesh"
            )
            self.log.debug("%s has single mesh: %s" % (
                transform, has_single_mesh))

            if not all([has_single_shape, has_single_mesh]):
                invalid.append(transform)

        if invalid:
            self.log.error(
                "'%s' has transforms with multiple shapes:\n%s" % (
                    instance,
                    ",\n".join(
                        "'" + member + "'" for member in invalid))
            )
            raise Exception("%s <Mesh Single Shape> Failed." % instance)

        self.log.info("%s <Mesh Single Shape> Passed." % instance)
