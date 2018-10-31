
import pyblish.api

from maya import cmds

from reveries.plugins import RepairInstanceAction
from reveries.maya.plugins import MayaSelectInvalidAction
import reveries.lib as lib


class RepairInvalid(RepairInstanceAction):

    label = "Reset Illegal Transforms"


class ValidateSetDressModelTransforms(pyblish.api.InstancePlugin):
    """Verify only root nodes of the loaded asset have transformations.

    Note: This check is temporary and is subject to change.

    Example outliner:
    <> means referenced
    ===================================================================

    setdress_GRP|
        props_GRP|
            barrel_01_:modelDefault|        [can have transforms]
                <> barrel_01_:barrel_GRP    [CAN'T have transforms]

            fence_01_:modelDefault|         [can have transforms]
                <> fence_01_:fence_GRP      [CAN'T have transforms]

    """

    order = pyblish.api.ValidatorOrder + 0.1
    label = "Setdress Transforms"
    families = ["reveries.setdress"]
    actions = [
        pyblish.api.Category("Select"),
        MayaSelectInvalidAction,
        pyblish.api.Category("Fix It"),
        RepairInvalid,
    ]

    prompt_message = ("You are about to reset the matrix to the default "
                      "values. This can alter the look of your scene. "
                      "Are you sure you want to continue?")

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found {} invalid transforms of setdress "
                               "items".format(len(invalid)))

    @staticmethod
    def get_invalid(instance):

        container_roots = instance.data["setdressRoots"]

        transforms_in_container = cmds.listRelatives(container_roots,
                                                     allDescendents=True,
                                                     type="transform",
                                                     fullPath=True)

        # Ensure all are identity matrix
        invalid = []
        for transform in transforms_in_container:
            node_matrix = cmds.xform(transform,
                                     query=True,
                                     matrix=True,
                                     objectSpace=True)
            if not lib.matrix_equals(node_matrix, lib.DEFAULT_MATRIX):
                invalid.append(transform)

        return invalid

    @classmethod
    def fix(cls, instance):
        """Reset matrix for illegally transformed nodes

        We want to ensure the user knows the reset will alter the look of
        the current scene because the transformations were done on asset
        nodes instead of the asset top node.

        Args:
            instance:

        Returns:
            None

        """
        from reveries.plugins import message_box_warning

        # Store namespace in variable, cosmetics thingy
        choice = message_box_warning(title="Matrix reset",
                                     message=cls.prompt_message,
                                     optional=True)

        invalid = cls.get_invalid(instance)
        if not invalid:
            cls.log.info("No invalid nodes")
            return

        if choice:
            cmds.xform(invalid, matrix=lib.DEFAULT_MATRIX, objectSpace=True)
