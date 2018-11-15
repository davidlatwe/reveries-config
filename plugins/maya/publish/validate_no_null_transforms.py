
import pyblish.api
import maya.cmds as cmds

from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidAction


class RepairInvalid(RepairInstanceAction):

    label = "Delete Empty/Null Transforms"


def has_shape_children(node):
    # Check if any descendants
    allDescendents = cmds.listRelatives(node,
                                        allDescendents=True,
                                        fullPath=True)
    if not allDescendents:
        return False

    # Check if there are any shapes at all
    shapes = cmds.ls(allDescendents, shapes=True)
    if not shapes:
        return False

    # Check if all descendent shapes are intermediateObjects;
    # if so we consider this node a null node and return False.
    if all(cmds.getAttr('{0}.intermediateObject'.format(x)) for x in shapes):
        return False

    return True


class ValidateNoNullTransforms(pyblish.api.InstancePlugin):
    """Ensure no null transforms are in the scene.

    Warning:
        Transforms with only intermediate shapes are also considered null
        transforms. These transform nodes could potentially be used in your
        construction history, so take care when automatically fixing this or
        when deleting the empty transforms manually.

    """

    order = pyblish.api.ValidatorOrder
    label = 'No Empty/Null Transforms'
    hosts = ['maya']
    families = ['reveries.model']
    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidAction,
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    @classmethod
    def get_invalid(cls, instance):
        """Return invalid transforms in instance"""

        transforms = cmds.ls(instance, type='transform', long=True)

        invalid = []
        for transform in transforms:
            if not has_shape_children(transform):
                invalid.append(transform)

        return invalid

    def process(self, instance):
        """Process all the transform nodes in the instance """
        invalid = self.get_invalid(instance)
        if invalid:
            raise ValueError("Empty transforms found: {0}".format(invalid))

    @classmethod
    def fix(cls, instance):
        """Delete all null transforms.

        Note: If the node is used elsewhere (eg. connection to attributes or
        in history) deletion might mess up things.

        """
        invalid = cls.get_invalid(instance)
        if invalid:
            cmds.delete(invalid)
