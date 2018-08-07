
import pyblish.api
from maya import cmds

from reveries.maya.lib import TRANSFORM_ATTRS


class ValidateRigAssembly(pyblish.api.InstancePlugin):
    """Ensure the content of the instance is grouped in a single hierarchy

    The instance must have a single root node containing all the content.
    This root node *must* be a top group in the outliner.

    """

    label = "Rig Assembly"
    order = pyblish.api.ValidatorOrder + 0
    hosts = ["maya"]
    families = ["reveries.rig"]

    def process(self, instance):

        root = cmds.ls(instance, assemblies=True)

        if not root == "RIG":
            self.log.error(
                "'%s' Must have a single root called 'RIG'." % (instance)
            )
            raise Exception("%s <Rig Assembly> Failed." % instance)

        # Validate Keyables
        #
        keyables = cmds.listAttr(root, keyable=True)

        # Transforms
        if any(attr in keyables for attr in TRANSFORM_ATTRS):
            self.log.error("Rig's assembly node 'RIG' should not have these "
                           "attributes keyable: {}".format(TRANSFORM_ATTRS))
            raise RuntimeError

        # Visibility
        if "visibility" not in keyables:
            self.log.error("visibility should be keyable.")
            raise RuntimeError

        # FacialConrtols
        # (TODO)

        # LowPoly Switch
        # (TODO)
