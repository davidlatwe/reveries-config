
import pyblish.api
from maya import cmds

from reveries import lib
from reveries.maya.plugins import MayaSelectInvalidAction


class ValidateTranformFreezed(pyblish.api.InstancePlugin):
    """ All transform must be freezed

    Checking `translate`, `rotate`, `scale` and `shear` are all freezed

    """

    order = pyblish.api.ValidatorOrder + 0.45
    hosts = ["maya"]
    label = "Transform Freezed"
    families = [
        "reveries.model",
        "reveries.rig",
    ]

    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidAction,
    ]

    @staticmethod
    def get_invalid(instance):
        """Returns the invalid transforms in the instance.

        This is the same as checking:
        - translate == [0, 0, 0] and rotate == [0, 0, 0] and
          scale == [1, 1, 1] and shear == [0, 0, 0]

        .. note::
            This will also catch camera transforms if those
            are in the instances.

        Returns:
            list: Transforms that are not identity matrix

        """

        invalid = list()

        _identity = [1.0, 0.0, 0.0, 0.0,
                     0.0, 1.0, 0.0, 0.0,
                     0.0, 0.0, 1.0, 0.0,
                     0.0, 0.0, 0.0, 1.0]
        _tolerance = 1e-30

        _ignoring = ("clusterHandle",)

        for transform in cmds.ls(instance, type="transform"):

            matrix = cmds.xform(transform,
                                query=True,
                                matrix=True,
                                objectSpace=True)

            if not lib.matrix_equals(_identity, matrix, _tolerance):
                ignore = False

                for shape in cmds.listRelatives(transform, shapes=True) or []:
                    if cmds.nodeType(shape) in _ignoring:
                        ignore = True
                        break

                if not ignore:
                    invalid.append(transform)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            self.log.error(
                "{!r} has not freezed transform:".format(instance.name)
            )
            for node in invalid:
                self.log.error(node)

            raise ValueError("%s <Transform Freezed> Failed." % instance.name)

        self.log.info("%s <Transform Freezed> Passed." % instance.name)
